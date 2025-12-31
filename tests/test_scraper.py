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


if __name__ == "__main__":  # pragma: no cover
    unittest.main()
