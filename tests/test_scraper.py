import unittest
from unittest.mock import Mock, patch

from swimmeet_scraper.scraper import SwimMeetScraper, SwimMeetScraperError


class ParseXmlPayloadTests(unittest.TestCase):
    def setUp(self) -> None:
        self.scraper = SwimMeetScraper()

    def test_parse_xml_results_block(self) -> None:
        payload = (
            "<results>"
            "<event name=\"Boys 200 Medley Relay\" date=\"February 17, 2024\" div=\"2\"></event>"
            "<result rk=\"1\" nm=\"A\" gr=\"\" sc=\"HVUS\" sh=\"University School\" shx=\"nhs\" ct=\"Hunting Valley\" st=\"OH\" ll=\"41.485518, -81.427641\" ti=\"1:35.28\" mt=\"nedistrict24\" auto=\"yes\"/>"
            "<result rk=\"2\" nm=\"A\" gr=\"\" sc=\"CIIH\" sh=\"Indian Hill\" ct=\"Cincinnati\" st=\"OH\" ll=\"39.186177, -84.347006\" ti=\"1:37.75\" mt=\"swdistrict24\" auto=\"yes\"/>"
            "</results>"
        )

        rows = self.scraper._parse_payload(payload.encode("utf-8"), "application/xml")

        self.assertEqual(
            rows,
            [
                {
                    "rk": "1",
                    "nm": "A",
                    "gr": "",
                    "sc": "HVUS",
                    "sh": "University School",
                    "shx": "nhs",
                    "ct": "Hunting Valley",
                    "st": "OH",
                    "ll": "41.485518, -81.427641",
                    "ti": "1:35.28",
                    "mt": "nedistrict24",
                    "auto": "yes",
                },
                {
                    "rk": "2",
                    "nm": "A",
                    "gr": "",
                    "sc": "CIIH",
                    "sh": "Indian Hill",
                    "ct": "Cincinnati",
                    "st": "OH",
                    "ll": "39.186177, -84.347006",
                    "ti": "1:37.75",
                    "mt": "swdistrict24",
                    "auto": "yes",
                },
            ],
        )

    def test_parse_xml_missing_results_raises(self) -> None:
        payload = "<results><event name=\"Boys 100 Backstroke\"></event></results>"

        with self.assertRaises(SwimMeetScraperError):
            self.scraper._parse_payload(payload.encode("utf-8"), "application/xml")

    def test_decode_error_raises_scraper_error(self) -> None:
        with self.assertRaises(SwimMeetScraperError):
            self.scraper._parse_payload(b"\xff\xfe\xfd", "application/xml")

    def test_fetch_event_logs_warning_and_skips_on_parse_error(self) -> None:
        scraper = SwimMeetScraper()

        with patch.object(scraper, "_build_url", return_value="http://example.com/foo"), patch(
            "swimmeet_scraper.scraper.urlopen"
        ) as mock_urlopen, patch.object(
            scraper, "_parse_payload", side_effect=SwimMeetScraperError("bad payload")
        ):
            mock_response = Mock()
            mock_response.headers.get.return_value = "application/xml"
            mock_response.read.return_value = b"irrelevant"
            mock_urlopen.return_value.__enter__.return_value = mock_response

            with self.assertLogs("swimmeet_scraper.scraper", level="WARNING") as log_output:
                rows = scraper.fetch_event("2023-2024", "finals", "girls", "d2", "foo", "ohio")

        self.assertEqual(rows, [])
        self.assertTrue(any("Skipping" in message for message in log_output.output))


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
