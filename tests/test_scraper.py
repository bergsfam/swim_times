import unittest

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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
