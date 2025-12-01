"""
Location configuration for Croatian županije (counties) and their districts.
Used for filtering scraping jobs by location.
"""

from typing import Dict, List, Optional

# Mapping of županije to their districts
ZUPANIJE: Dict[str, List[str]] = {
    "Varaždinska": [
        "Gornji Kneginec",
        "Ivanec",
        "Lepoglava",
        "Ludbreg",
        "Maruševec",
        "Novi Marof",
        "Petrijanec",
        "Sračinec",
        "Trnovec Bartolovečki",
        "Varaždin",
        "Varaždin - Okolica",
        "Varaždinske Toplice",
        "Veliki Bukovec",
        "Visoko",
    ],
    "Zagrebačka": [
        "Brdovec",
        "Dugo Selo",
        "Ivanić-Grad",
        "Jastrebarsko",
        "Samobor",
        "Sveta Nedelja",
        "Sveti Ivan Zelina",
        "Velika Gorica",
        "Vrbovec",
        "Zaprešić",
    ],
    "Grad Zagreb": [
        "Brezovica",
        "Centar",
        "Črnomerec",
        "Donja Dubrava",
        "Donji Grad",
        "Gornja Dubrava",
        "Gornji Grad - Medveščak",
        "Maksimir",
        "Novi Zagreb - istok",
        "Novi Zagreb - zapad",
        "Pešćenica - Žitnjak",
        "Podsljeme",
        "Podsused - Vrapče",
        "Sesvete",
        "Stenjevec",
        "Trešnjevka - jug",
        "Trešnjevka - sjever",
        "Trnje",
    ],
    "Krapinsko-zagorska": [
        "Bedekovčina",
        "Donja Stubica",
        "Gornja Stubica",
        "Klanjec",
        "Krapina",
        "Krapinske Toplice",
        "Marija Bistrica",
        "Oroslavje",
        "Pregrada",
        "Zabok",
        "Zlatar",
    ],
    "Sisačko-moslavačka": [
        "Glina",
        "Hrvatska Kostajnica",
        "Kutina",
        "Novska",
        "Petrinja",
        "Popovača",
        "Sisak",
    ],
    "Karlovačka": [
        "Duga Resa",
        "Karlovac",
        "Ogulin",
        "Ozalj",
        "Slunj",
    ],
    "Bjelovarsko-bilogorska": [
        "Bjelovar",
        "Čazma",
        "Daruvar",
        "Garešnica",
        "Grubišno Polje",
    ],
    "Primorsko-goranska": [
        "Bakar",
        "Cres",
        "Crikvenica",
        "Čabar",
        "Delnice",
        "Kastav",
        "Kraljevica",
        "Krk",
        "Mali Lošinj",
        "Novi Vinodolski",
        "Opatija",
        "Rab",
        "Rijeka",
        "Vrbovsko",
    ],
    "Ličko-senjska": [
        "Gospić",
        "Novalja",
        "Otočac",
        "Senj",
    ],
    "Virovitičko-podravska": [
        "Orahovica",
        "Pitomača",
        "Slatina",
        "Virovitica",
    ],
    "Požeško-slavonska": [
        "Kutjevo",
        "Lipik",
        "Pakrac",
        "Pleternica",
        "Požega",
    ],
    "Brodsko-posavska": [
        "Nova Gradiška",
        "Slavonski Brod",
    ],
    "Zadarska": [
        "Benkovac",
        "Biograd na Moru",
        "Nin",
        "Obrovac",
        "Pag",
        "Zadar",
    ],
    "Osječko-baranjska": [
        "Beli Manastir",
        "Belišće",
        "Donji Miholjac",
        "Đakovo",
        "Našice",
        "Osijek",
        "Valpovo",
    ],
    "Šibensko-kninska": [
        "Drniš",
        "Knin",
        "Skradin",
        "Šibenik",
        "Vodice",
    ],
    "Vukovarsko-srijemska": [
        "Ilok",
        "Otok",
        "Vinkovci",
        "Vukovar",
        "Županja",
    ],
    "Splitsko-dalmatinska": [
        "Hvar",
        "Imotski",
        "Kaštela",
        "Komiža",
        "Makarska",
        "Omiš",
        "Sinj",
        "Solin",
        "Split",
        "Stari Grad",
        "Supetar",
        "Trilj",
        "Trogir",
        "Vis",
        "Vrgorac",
        "Vrlika",
    ],
    "Istarska": [
        "Buje",
        "Buzet",
        "Labin",
        "Novigrad",
        "Pazin",
        "Poreč",
        "Pula",
        "Rovinj",
        "Umag",
        "Vodnjan",
    ],
    "Dubrovačko-neretvanska": [
        "Dubrovnik",
        "Korčula",
        "Metković",
        "Opuzen",
        "Ploče",
    ],
    "Međimurska": [
        "Čakovec",
        "Mursko Središće",
        "Prelog",
    ],
    "Koprivničko-križevačka": [
        "Đurđevac",
        "Koprivnica",
        "Križevci",
    ],
}

# URL slugs for njuskalo.hr - mapping district names to URL-friendly versions
DISTRICT_URL_SLUGS: Dict[str, str] = {
    # Varaždinska
    "Gornji Kneginec": "gornji-kneginec",
    "Ivanec": "ivanec",
    "Lepoglava": "lepoglava",
    "Ludbreg": "ludbreg",
    "Maruševec": "marusevec",
    "Novi Marof": "novi-marof",
    "Petrijanec": "petrijanec",
    "Sračinec": "sracinec",
    "Trnovec Bartolovečki": "trnovec-bartolovecki",
    "Varaždin": "varazdin",
    "Varaždin - Okolica": "varazdin-okolica",
    "Varaždinske Toplice": "varazdinske-toplice",
    "Veliki Bukovec": "veliki-bukovec",
    "Visoko": "visoko",
    # Add more as needed...
}

# Županija URL slugs for njuskalo.hr
ZUPANIJA_URL_SLUGS: Dict[str, str] = {
    "Varaždinska": "varazdinska",
    "Zagrebačka": "zagrebacka",
    "Grad Zagreb": "grad-zagreb",
    "Krapinsko-zagorska": "krapinsko-zagorska",
    "Sisačko-moslavačka": "sisacko-moslavacka",
    "Karlovačka": "karlovacka",
    "Bjelovarsko-bilogorska": "bjelovarsko-bilogorska",
    "Primorsko-goranska": "primorsko-goranska",
    "Ličko-senjska": "licko-senjska",
    "Virovitičko-podravska": "viroviticko-podravska",
    "Požeško-slavonska": "pozesko-slavonska",
    "Brodsko-posavska": "brodsko-posavska",
    "Zadarska": "zadarska",
    "Osječko-baranjska": "osjecko-baranjska",
    "Šibensko-kninska": "sibensko-kninska",
    "Vukovarsko-srijemska": "vukovarsko-srijemska",
    "Splitsko-dalmatinska": "splitsko-dalmatinska",
    "Istarska": "istarska",
    "Dubrovačko-neretvanska": "dubrovacko-neretvanska",
    "Međimurska": "medimurska",
    "Koprivničko-križevačka": "koprivnicko-krizevacka",
}


def get_all_zupanije() -> List[str]:
    """Get list of all županije names."""
    return list(ZUPANIJE.keys())


def get_districts(zupanija: str) -> List[str]:
    """Get districts for a specific županija."""
    return ZUPANIJE.get(zupanija, [])


def get_zupanija_slug(zupanija: str) -> str:
    """Get URL slug for a županija."""
    return ZUPANIJA_URL_SLUGS.get(zupanija, zupanija.lower().replace(" ", "-"))


def get_district_slug(district: str) -> str:
    """Get URL slug for a district."""
    if district in DISTRICT_URL_SLUGS:
        return DISTRICT_URL_SLUGS[district]
    # Fallback: convert to slug
    return district.lower().replace(" - ", "-").replace(" ", "-").replace("č", "c").replace("ć", "c").replace("š", "s").replace("ž", "z").replace("đ", "d")


def build_search_url(zupanija: str, district: Optional[str] = None, property_type: str = "prodaja-stanova") -> str:
    """
    Build a njuskalo.hr search URL for a location.
    
    Args:
        zupanija: The županija name
        district: Optional district name (if None, searches whole županija)
        property_type: Type of property listing (default: prodaja-stanova)
    
    Returns:
        Full njuskalo.hr search URL
    """
    base_url = "https://www.njuskalo.hr"
    
    if district:
        district_slug = get_district_slug(district)
        return f"{base_url}/{property_type}/{district_slug}"
    else:
        zupanija_slug = get_zupanija_slug(zupanija)
        return f"{base_url}/{property_type}/{zupanija_slug}"

