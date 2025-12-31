import unittest

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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
