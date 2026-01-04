import socket
import ssl

SUPPORTED_SCHEMES = frozenset(["http", "https", "file", "data"])

class URL:
    """URL 파싱 담당 - URL 문자열을 분석하여 구성 요소로 분리"""

    is_view_source: bool = False

    def __init__(self, url: str):
            
        # 스킴 추출
        if url.startswith("data:"):
            self.scheme = "data"
        
        elif url.startswith("file:"):
            self.scheme = "file"
        
        elif url.startswith('view-source:'):
            self.is_view_source = True
            sliced_url = url[len('view-source:'):]
            self.scheme, url = sliced_url.split("://", 1)
        
        elif "://" in url:
            self.scheme, url = url.split("://", 1)
        
        else:
            self.scheme = None

        # 지원하는 스킴인지 확인 후 예외처리
        # - view-source는 내부 플래그로 처리하므로 제외
        assert self.scheme in SUPPORTED_SCHEMES, "지원하지 않는 스킴입니다."

        # data 스킴 처리
        if self.scheme == 'data':
            self.path = url
            self.host = ''
            self.port = None
            return
        
        # file 스킴 처리
        if self.scheme == "file":
            self.path = url
            self.host = ''
            self.port = None
            return

        # url에서 호스트와 경로를 분리한다.
        if "/" not in url:
            url = url + '/'

        self.host, url = url.split("/", 1)
        self.path = "/" + url

        # 사용자 지정 포트 처리
        if ":" in self.host:
            self.host, port = self.host.split(":", 1)
            self.port = int(port)
        else:
            # 기본 포트 설정
            self.port = 443 if self.scheme == "https" else 80


class HttpClient:
    """HTTP 통신 담당 - 소켓 연결, 요청 전송, 응답 수신"""

    USER_AGENT = "DannyTestBrowser/0.1"

    def __init__(self, url: URL):
        self.url = url

    def _create_socket(self):
        """소켓 생성 및 SSL 래핑"""
        s = socket.socket(
            family=socket.AF_INET6,
            type=socket.SOCK_STREAM,
            proto=socket.IPPROTO_TCP,
        )

        if self.url.scheme == "https":
            ctx = ssl.create_default_context()
            s = ctx.wrap_socket(s, server_hostname=self.url.host)

        return s

    def _build_request(self) -> str:
        """HTTP 요청 문자열 생성"""
        request = f"GET {self.url.path} HTTP/1.1\r\n"
        request += f"Host: {self.url.host}\r\n"
        request += f"User-Agent: {self.USER_AGENT}\r\n"
        request += "Connection: close\r\n"
        request += "\r\n"
        return request

    def _parse_status_line(self, response) -> tuple[str, str, str]:
        """상태 라인 파싱"""
        status_line = response.readline()
        version, status, explanation = status_line.split(" ", 2)
        return version, status, explanation.strip()

    def _parse_headers(self, response) -> dict:
        """헤더 파싱"""
        headers = {}
        while True:
            line = response.readline()
            if line == "\r\n":
                break
            header, value = line.split(":", 1)
            headers[header.casefold()] = value.strip()
        return headers

    def _read_body(self, response, headers: dict) -> str:
        """응답 본문 읽기 - 인코딩 방식에 따라 처리"""
        # 청크 인코딩된 응답 처리
        if "transfer-encoding" in headers:
            return self._read_chunked_body(response)
        # Content-Length가 명시된 응답 처리
        elif "content-length" in headers:
            length = int(headers["content-length"])
            return response.read(length)
        # 그 외 (Connection: close에 의존)
        else:
            return response.read()

    def _read_chunked_body(self, response) -> str:
        """청크 인코딩된 응답 본문 읽기"""
        body = ""
        while True:
            size_line = response.readline().strip()
            size = int(size_line, 16)

            if size == 0:
                break

            chunk = response.read(size)
            body += chunk
            response.readline()  # 청크 뒤의 \r\n 소비

        return body

    def fetch(self) -> str:
        """HTTP 요청을 수행하고 응답 본문을 반환"""
        print(f"-----------------------------------")
        print(f"📌 Connecting to {self.url.host}:...")

        s = self._create_socket()
        s.connect((self.url.host, self.url.port))

        # 요청 전송
        print(f"-----------------------------------")
        print('📌 Sending request...')
        print(f"  scheme: {self.url.scheme}")
        print(f"  host: {self.url.host}")
        print(f"  path: {self.url.path}")
        print(f"  port: {self.url.port}")

        request = self._build_request()
        s.send(request.encode("utf-8"))

        # 응답 수신
        response = s.makefile("r", encoding="utf-8", newline="\r\n")

        version, status, explanation = self._parse_status_line(response)
        print('-----------------------------------')
        print('📌 Response status line:')
        print(f"  Version: {version}")
        print(f"  Status: {status}")
        print(f"  Explanation: {explanation}")

        headers = self._parse_headers(response)
        print('-----------------------------------')
        print('📌 Response headers:')
        for header, value in headers.items():
            print(f"  {header}: {value}")

        # 실습 프로젝트이므로 압축 인코딩을 사용하지 않는 응답만 처리
        assert "content-encoding" not in headers

        body = self._read_body(response, headers)

        s.close()
        return body


class HtmlRenderer:
    """HTML 렌더링 담당 - HTML 태그를 제거하고 텍스트만 출력"""

    @staticmethod
    def strip_tags(html: str) -> str:
        """HTML 태그를 제거하고 텍스트만 반환"""
        result = ""
        in_tag = False
        for c in html:
            if c == "<":
                in_tag = True
            elif c == ">":
                in_tag = False
            elif not in_tag:
                result += c
        return result

    @staticmethod
    def render(html_string: str):
        import html

        """HTML을 렌더링하여 출력"""
        print('-----------------------------------')
        print("📌 Response body:")
        text = HtmlRenderer.strip_tags(html_string)
        unescaped_text = html.unescape(text)
        print(unescaped_text)

class ViewSourceRenderer:
    """뷰 소스 렌더링 담당 - 소스 코드를 출력"""

    @staticmethod
    def render(source: str):
        import html

        print('-----------------------------------')
        print("📌 View Source:")
        unescaped_source = html.unescape(source)
        print(unescaped_source)

class FileRenderer: 
    """파일 렌더링 담당 - 파일 내용을 출력"""

    @staticmethod
    def render(url_path: str):
        import mimetypes

        mime_guess_type = mimetypes.guess_type(url_path)[0]

        is_image = mime_guess_type.startswith("image/")
        is_text = mime_guess_type.startswith("text/")

        if is_image:
            # 바이너리로 읽기
            with open(url_path, "rb") as f:
                body = f.read()
            print(f"-----------------------------------")
            print(f"✅ 이미지 파일 읽기 성공")
            print(f"-----------------------------------")
            print(f"    파일 크기: {len(body)} bytes")
            return

        if is_text:
            with open(url_path, "r", encoding="utf-8") as f:
                body = f.read()
            print(f"-----------------------------------")
            print(f"✅ 텍스트 파일 읽기 성공")
            print(f"-----------------------------------")
            print(f"")
            print(f"{body}")
            print(f"")
            return
        

class Browser:
    """브라우저 - URL을 받아 페이지를 로드하고 렌더링"""

    def load(self, url_string: str):
        url = URL(url_string)
        
        if url.scheme == "data":
            print(f"-----------------------------------")
            print(f"✅ data scheme 처리")
            print(f"-----------------------------------")
            print(f"    데이터: {url.path}")
            return

        if url.scheme == "file":
            FileRenderer.render(url.path)
            return
        
        client = HttpClient(url)
        body = client.fetch()

        if url.is_view_source:
            ViewSourceRenderer.render(body)
        else:
            HtmlRenderer.render(body)


if __name__ == "__main__":
    import sys
    from urllib.parse import unquote

    # 입력된 URL 디코딩 처리
    decoded_url = unquote(sys.argv[1])
    browser = Browser()
    browser.load(decoded_url)