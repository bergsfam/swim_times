import unittest
from unittest import mock

from swimmeet_scraper.scraper import SwimMeetScraper, SwimMeetScraperError


class ParseXmlPayloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scraper = SwimMeetScraper()

    def test_parse_xml_results_block(self) -> None:
        payload = (
            "<html><xml>"
            "<results>"
            "<event name=\"Boys 100 Backstroke\" date=\"February 17, 2024\" div=\"2\"></event>"
            "<result rk=\"1\" nm=\"Krys Gorski\" gr=\"Sr\" sc=\"WAN\" ti=\"48.92\" mt=\"nedistrict24\" auto=\"yes\"></result>"
            "<result rk=\"2\" nm=\"Jane Doe\" gr=\"Jr\" sc=\"SOM\" ti=\"50.10\" mt=\"nedistrict24\"></result>"
            "</results>"
            "</xml></html>"
        )

        rows = self.scraper._parse_payload(payload.encode("utf-8"), "text/html")

        self.assertEqual(
            rows,
            [
                {"rk": "1", "nm": "Krys Gorski", "gr": "Sr", "sc": "WAN", "ti": "48.92", "mt": "nedistrict24", "auto": "yes"},
                {"rk": "2", "nm": "Jane Doe", "gr": "Jr", "sc": "SOM", "ti": "50.10", "mt": "nedistrict24", "auto": ""},
            ],
        )

    def test_parse_xml_missing_results_raises(self) -> None:
        payload = "<html><xml><event name=\"Boys 100 Backstroke\"></event></xml></html>"

        with self.assertRaises(SwimMeetScraperError):
            self.scraper._parse_payload(payload.encode("utf-8"), "text/html")

    def test_parse_xml_with_uppercase_tags(self) -> None:
        payload = (
            "<html><XML><RESULTS>"
            "<RESULT rk=\"1\" nm=\"Swimmer One\" gr=\"Sr\" sc=\"AAA\" ti=\"50.00\" mt=\"meet\"></RESULT>"
            "<result rk=\"2\" nm=\"Swimmer Two\" gr=\"Jr\" sc=\"BBB\" ti=\"51.00\" mt=\"meet\" auto=\"yes\"></result>"
            "</RESULTS></XML></html>"
        )

        rows = self.scraper._parse_payload(payload.encode("utf-8"), "text/xml")

        self.assertEqual(
            rows,
            [
                {"rk": "1", "nm": "Swimmer One", "gr": "Sr", "sc": "AAA", "ti": "50.00", "mt": "meet", "auto": ""},
                {"rk": "2", "nm": "Swimmer Two", "gr": "Jr", "sc": "BBB", "ti": "51.00", "mt": "meet", "auto": "yes"},
            ],
        )

    def test_parse_html_escaped_xml_content(self) -> None:
        payload = (
            "<html><script>var xml = \"&lt;xml&gt;"
            "&lt;results&gt;"
            "&lt;result rk='1' nm='Encoded Swimmer' sc='ABC' ti='49.99' mt='encoded' auto='yes' /&gt;"
            "&lt;/results&gt;"
            "&lt;/xml&gt;\";</script></html>"
        )

        rows = self.scraper._parse_payload(payload.encode("utf-8"), "text/html")

        self.assertEqual(
            rows,
            [
                {
                    "rk": "1",
                    "nm": "Encoded Swimmer",
                    "gr": "",
                    "sc": "ABC",
                    "ti": "49.99",
                    "mt": "encoded",
                    "auto": "yes",
                }
            ],
        )


class PlaywrightFallbackTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scraper = SwimMeetScraper()

    def _response(self, payload: str, content_type: str):
        class _MockResponse:
            def __init__(self, body: str, content_type: str):
                self.body = body
                self.content_type = content_type

            def __enter__(self):
                return self

            def __exit__(self, exc_type, exc_val, exc_tb):
                return False

            def read(self) -> bytes:
                return self.body.encode("utf-8")

            @property
            def headers(self):
                return {"Content-Type": self.content_type}

        return _MockResponse(payload, content_type)

    @mock.patch("swimmeet_scraper.scraper.urlopen")
    def test_render_js_fallback_on_parse_error(self, mock_urlopen: mock.Mock) -> None:
        mock_urlopen.return_value = self._response(
            "<html><xml><results></results></xml></html>", "text/html"
        )

        rendered = (
            "<html><xml>"
            "<results>"
            "<result rk=\"1\" nm=\"Rendered Swimmer\" sc=\"AAA\" ti=\"55.00\" mt=\"meet\"></result>"
            "</results>"
            "</xml></html>"
        )

        with mock.patch.object(
            self.scraper,
            "_fetch_with_playwright",
            return_value=rendered.encode("utf-8"),
        ) as mock_render:
            rows = self.scraper.fetch_event(
                season="2023-2024",
                phase="compilation",
                gender="girls",
                division="d2",
                event_slug="relay",
                state="ohio",
                render_js=True,
            )

        mock_render.assert_called_once()
        self.assertEqual(
            rows,
            [
                {
                    "rk": "1",
                    "nm": "Rendered Swimmer",
                    "gr": "",
                    "sc": "AAA",
                    "ti": "55.00",
                    "mt": "meet",
                    "auto": "",
                }
            ],
        )

    @mock.patch("swimmeet_scraper.scraper.urlopen")
    def test_render_js_disabled_raises_parse_error(self, mock_urlopen: mock.Mock) -> None:
        mock_urlopen.return_value = self._response(
            "<html><xml><results></results></xml></html>", "text/html"
        )

        with self.assertRaises(SwimMeetScraperError):
            self.scraper.fetch_event(
                season="2023-2024",
                phase="compilation",
                gender="girls",
                division="d2",
                event_slug="relay",
                state="ohio",
                render_js=False,
            )


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
