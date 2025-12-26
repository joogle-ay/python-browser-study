import socket
import ssl

class URL:
    def __init__(self, url: str):
        
        # 실습을 위한 프로젝트이므로, 간단한 처리를 위해 모든 스킴은 http라고 전제한다.
        # 스킴이 명시되지 않은 경우 http로 간주한다.
        if "://" in url:
            self.scheme, url = url.split("://", 1)
        else:
            self.scheme = "http"

        assert self.scheme in ["http", "https"]

        # url에서 호스트와 경로를 분리한다.
        if "/" not in url:
            url = url + '/'


        self.host, url = url.split("/", 1)
        self.path = "/" + url
        
        print(f"-----------------------------------")
        print(f"📌 Connecting to {self.host}:...")

        # 사용자 지정 포트 처리
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)

    def request(self):
        s = socket.socket(
            family=socket.AF_INET6,  # IPv6 (localhost가 IPv6로 바인딩된 경우 대응)
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )

        if self.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.host)

        # 기본 포트 설정 (포트가 지정되지 않은 경우에만)
        if not hasattr(self, 'port'):
            if self.scheme == "https":
                self.port = 443
            else:
                self.port = 80


        print(f"-----------------------------------")
        print('📌 Sending request...')
        print(f"  host: {self.host}")
        print(f"  path: {self.path}") 
        print(f"  port: {self.port}")

        s.connect((self.host, self.port))

        # format => f-string의 구버전 문법
        request = "GET {} HTTP/1.1\r\n".format(self.path)
        request += "Host: {}\r\n".format(self.host)
        request += "User-Agent: DannyTextBrowser/0.1\r\n"
        request += "Connection: close\r\n"  # 응답 완료 후 연결 종료
        request += "\r\n"
        s.send(request.encode("utf-8"))

        # 소켓을 파일 객체로 감싼다.
        response = s.makefile("r", encoding="utf-8", newline="\r\n")

        # HTTP 응답의 첫 번째 줄(상태 라인)을 읽어들인다.
        status_line = response.readline()
        version, status, explanation = status_line.split(" ", 2)

        print('-----------------------------------')
        print('📌 Response status line:')
        print(f"  Version: {version}")
        print(f"  Status: {status}")
        print(f"  Explanation: {explanation.strip()}")

        # status_line 이후의 헤더들을 모두 읽어들인다.
        # response.readline()을 반복 호출하여 헤더의 끝을 나타내는 빈 줄("\r\n")이 나올 때까지 읽는다.
        # response.readline()은 호출할때마다 다음 라인으로 이동하므로, 본 반복문을 도는 시점에 상태 코드는 읽지 않는다.
        response_headers = {}
        while True:
            line = response.readline()
            if line == "\r\n": break
            header, value = line.split(":", 1)
            response_headers[header.casefold()] = value.strip()

        print('-----------------------------------')
        print('📌 Response headers:')
        for header, value in response_headers.items():
            print(f"  {header}: {value}")

        # 실습 프로젝트이므로 압축 인코딩을 사용하지 않는 응답만 처리한다.
        assert "content-encoding" not in response_headers

        # 헤더 이후의 응답 본문을 읽어들인다.
        # 청크 인코딩된 응답과 아닌 응답을 구분하여 처리한다.
        if "transfer-encoding" in response_headers:
            # 청크 인코딩된 응답 처리
            body = ""
            while True:
                # 청크 크기 읽기 (16진수 문자열)
                size_line = response.readline().strip()
                size = int(size_line, 16)

                if size == 0:
                    break

                # 해당 크기만큼 데이터 읽기
                chunk = response.read(size)
                body += chunk

                response.readline()  # 청크 뒤의 \r\n 소비

        # Content-Length가 명시된 응답 처리
        elif "content-length" in response_headers:
            length = int(response_headers["content-length"])
            body = response.read(length)
        
        else:
            body = response.read()

        # 소켓과 파일 객체 닫기
        s.close()

        return body

## 간단한 HTML 태그 제거기 (학습용)
def show(body):
    in_tag = False
    for c in body:
        if c == "<":
            in_tag = True
        elif c == ">":
            in_tag = False
        elif not in_tag:
            print(c, end="")

def load(url):
    body = url.request()
    print('-----------------------------------')
    print("📌 Response body:")
    show(body)

if __name__ == "__main__":
    import sys
    load(URL(sys.argv[1]))



