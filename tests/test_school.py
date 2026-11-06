"""Offline test van custom_templates/school.jinja met nagebootste HA-functies.

Draaien:  python3 -m venv .venv && .venv/bin/pip install jinja2
          .venv/bin/python tests/test_school.py

Dekt de roosterregels die met magister_school v2.3.1 zijn veranderd (oktober
2026): de `categorie` les / afspraak / boeking, `herhalend_elke_werkdag`, het
05:00-18:00-venster, en de splitsing tussen begin (lessen + echte afspraken) en
"uit om" (alleen echte lessen). Plus de regels van daarvoor die niet stuk mogen:
een les met huiswerk blijft een les, 00:00-items zijn geen lesuur, vervallen
uren staan apart.

De afspraken lijken bewust op wat Logans school echt levert (live bekeken op
31-10-2026): roostercodes als omschrijving, "Coachgesprek Logan" als afspraak
met docent maar zonder vak, lokalen dubbel ("603, 603") van vóór v2.3.1.
"""
import datetime as dt
import json
import os
import re

from jinja2 import Environment, FileSystemLoader

CONFIG = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KIND = "sensor.magister_logan_veen"

STATES = {}
ATTRS = {}
KLOK = {"nu": dt.datetime(2026, 11, 3, 7, 30, 0)}


def ha_strptime(value, fmt, default=None):
    try:
        return dt.datetime.strptime(str(value), fmt)
    except (TypeError, ValueError):
        return default


def ha_regex_replace(value, find="", replace="", ignorecase=False):
    return re.sub(find, replace, str(value), flags=re.I if ignorecase else 0)


def ha_match(value, pattern="", ignorecase=False):
    return bool(re.match(pattern, str(value), flags=re.I if ignorecase else 0))


def ha_search(value, pattern="", ignorecase=False):
    return bool(re.search(pattern, str(value), flags=re.I if ignorecase else 0))


def ha_is_number(value):
    try:
        float(value)
        return True
    except (TypeError, ValueError):
        return False


env = Environment(loader=FileSystemLoader(f"{CONFIG}/custom_templates"))
env.filters["to_json"] = lambda v, **k: json.dumps(v)
env.filters["from_json"] = json.loads
env.filters["regex_replace"] = ha_regex_replace
env.tests["match"] = ha_match
env.tests["search"] = ha_search
env.tests["is_number"] = ha_is_number
env.globals.update(
    now=lambda: KLOK["nu"],
    timedelta=dt.timedelta,
    strptime=ha_strptime,
    states=lambda eid: STATES.get(eid, "unknown"),
    state_attr=lambda eid, attr: ATTRS.get(eid, {}).get(attr),
)

MOD = env.get_template("school.jinja").module


# ---------------------------------------------------------------------------
# Afspraken bouwen
# ---------------------------------------------------------------------------
def afspraak(start, einde, omschrijving, vak="", docent="", soort="Les",
             lokaal="603, 603", categorie=None, **kw):
    a = {
        "start": start, "einde": einde, "omschrijving": omschrijving,
        "vak": vak, "docent": docent, "docentcode": "", "soort": soort,
        "type": "", "lokaal": lokaal, "status": "Geroosterd", "inhoud": None,
        "opmerking": None, "is_uitval": False, "is_huiswerk": False,
        "is_online": False, "is_afgerond": False, "duurt_hele_dag": False,
        "was_afwijkend": False, "lesuurstart": None, "lesuureinde": None,
    }
    if categorie is not None:  # v2.3.1; zonder = de oude integratie
        a["categorie"] = categorie
    a.update(kw)
    return a


def les(d, van, tot, code, vak, docent="B. Docent", **kw):
    return afspraak(f"{d} {van}:00", f"{d} {tot}:00", f"{code} - xx - uhv1d",
                    vak, docent, "Les", categorie=kw.pop("categorie", "les"), **kw)


DI = "2026-11-03"
WO = "2026-11-04"


def dinsdag(*extra, categorie=True):
    """Dinsdag zoals hij echt was: coachgesprek 08:30, zes lessen tot 14:00."""
    items = [
        afspraak(f"{DI} 08:30:00", f"{DI} 08:45:00", "Coachgesprek Logan", "",
                 "A. Mentor", "Algemeen", "600", "afspraak"),
        les(DI, "08:45", "09:30", "LO", "lichamelijke opvoeding", lokaal="Z2, Z2 gymzaal"),
        les(DI, "09:30", "10:15", "LO", "lichamelijke opvoeding"),
        les(DI, "10:15", "11:00", "TN", "techniek", is_huiswerk=True),
        les(DI, "11:15", "12:00", "TN", "techniek"),
        les(DI, "12:00", "12:45", "WI", "wiskunde"),
        les(DI, "13:15", "14:00", "GS", "geschiedenis"),
        # Huiswerk zonder les: een dagitem van 00:00, geen lesuur.
        afspraak(f"{DI} 00:00:00", f"{WO} 00:00:00", "AK", "aardrijkskunde",
                 "C. Docent", "Algemeen", "", "afspraak", type="Huiswerk",
                 is_huiswerk=True),
        les(WO, "08:45", "09:45", "CT_BG", "Coachtijd/Basisgroep"),
        les(WO, "09:50", "10:50", "EN", "Engels"),
    ]
    items += list(extra)
    if not categorie:
        for a in items:
            a.pop("categorie", None)
    return items


def wereld(afspraken, om=None):
    STATES.clear()
    ATTRS.clear()
    STATES[KIND] = "0"
    ATTRS[KIND] = {"afspraken": afspraken}
    STATES["sensor.magister_data"] = "2026-11-03T07:00:00"
    ATTRS["sensor.magister_data"] = {"kinderen": {"Logan Veen": {"afspraken": afspraken}}}
    if om:
        KLOK["nu"] = dt.datetime.strptime(om, "%Y-%m-%d %H:%M")


FOUTEN = []


def bevat(naam, tekst, *delen, niet=()):
    mis = [d for d in delen if d not in tekst] + [d for d in niet if d in tekst]
    print(f"{'PASS' if not mis else 'FAIL'}  {naam}")
    if mis:
        FOUTEN.append(f"{naam}: {mis!r} klopt niet in\n{tekst}")


def gelijk(naam, gekregen, verwacht):
    ok = gekregen == verwacht
    print(f"{'PASS' if ok else 'FAIL'}  {naam:60} -> {gekregen!r}")
    if not ok:
        FOUTEN.append(f"{naam}: kreeg {gekregen!r}, verwachtte {verwacht!r}")


def nu():
    return MOD.nu(KIND)


def lessen(d=DI):
    return [a["omschrijving"] for a in json.loads(MOD.lessen_json(KIND, d))]


# ---------------------------------------------------------------------------
# 1. Begin = eerste les óf echte afspraak; uit om = laatste échte les
# ---------------------------------------------------------------------------
wereld(dinsdag(), f"{DI} 07:30")
bevat("coachgesprek bepaalt de begintijd", nu(), "### Begint om 08:30")
bevat("afspraak zonder vak krijgt zijn omschrijving, geen lege vaknaam", nu(),
      "Eerst **Coachgesprek Logan** in 600", niet=("****",))
bevat("uren tellen alleen lessen, uit om de laatste les", nu(), "6 uren, uit om **14:00**")
gelijk("een les met huiswerk blijft op het rooster", "TN - xx - uhv1d" in lessen(), True)
gelijk("het 00:00-huiswerkitem is geen lesuur", "AK" in lessen(), False)

# ---------------------------------------------------------------------------
# 2. Boeking: niet op het rooster, wel gedempt in de tabel
# ---------------------------------------------------------------------------
studie = afspraak(f"{DI} 14:15:00", f"{DI} 16:00:00", "Studie na school", "", "",
                  "Algemeen", "Studieruimte", "boeking")
wereld(dinsdag(studie), f"{DI} 07:30")
bevat("boeking duwt 'uit om' niet op", nu(), "uit om **14:00**", niet=("16:00", "Studie"))
gelijk("boeking staat niet in lessen_json", "Studie na school" in lessen(), False)
bevat("boeking staat gedempt in de roostertabel", MOD.rooster(KIND, DI),
      "*Studie na school* · optioneel", niet=("**Studie na school**",))

# Dezelfde boeking zonder `categorie` (integratie van vóór v2.3.1): herkend
# aan het ontbreken van vak en docent.
wereld(dinsdag(dict(studie), categorie=False), f"{DI} 07:30")
gelijk("zonder categorie: boeking herkend aan geen vak/docent", "Studie na school" in lessen(), False)
gelijk("zonder categorie: coachgesprek (wel docent) telt mee",
       "Coachgesprek Logan" in lessen(), True)

# ---------------------------------------------------------------------------
# 3. Herhalend elke werkdag, avondactiviteit, bloksoort
# ---------------------------------------------------------------------------
vroeg = afspraak(f"{DI} 07:30:00", f"{DI} 08:30:00", "Studie voor school", "",
                 "D. Docent", "Algemeen", "500", "afspraak", herhalend=True,
                 herhalend_elke_werkdag=True)
avond = afspraak(f"{DI} 19:00:00", f"{DI} 20:40:00", "Ouderavond", "",
                 "A. Mentor", "Algemeen", "aula", "afspraak")
blok = afspraak(f"{DI} 08:00:00", f"{DI} 08:30:00", "Blokkade", "", "D. Docent",
                "Blokkade", "", "afspraak")
wereld(dinsdag(vroeg, avond, blok), f"{DI} 07:00")
bevat("elke werkdag terugkerend item zet de begintijd niet vroeger", nu(), "### Begint om 08:30")
gelijk("avondactiviteit (na 18:00) staat niet op het rooster", "Ouderavond" in lessen(), False)
gelijk("bloksoort staat nergens", "Blokkade" in MOD.rooster(KIND, DI), False)
bevat("avondactiviteit wel gedempt in de tabel", MOD.rooster(KIND, DI), "*Ouderavond* · optioneel")

# ---------------------------------------------------------------------------
# 4. Een afspraak na de laatste les
# ---------------------------------------------------------------------------
mentor = afspraak(f"{DI} 15:00:00", f"{DI} 15:30:00", "Mentorgesprek", "",
                  "A. Mentor", "Algemeen", "600", "afspraak")
wereld(dinsdag(mentor), f"{DI} 07:30")
bevat("'s ochtends: uit om 14:00 en daarna nog het gesprek", nu(),
      "uit om **14:00**", "Daarna nog **Mentorgesprek** om 15:00")
wereld(dinsdag(mentor), f"{DI} 13:30")
bevat("tijdens de laatste les", nu(), "### Nu: Geschiedenis", "Laatste les.",
      "Daarna nog **Mentorgesprek** om 15:00", niet=("Hierna",))
wereld(dinsdag(mentor), f"{DI} 14:30")
bevat("tussen laatste les en gesprek: geen tussenuur", nu(),
      "### Lessen klaar sinds 14:00", "Om 15:00 nog **Mentorgesprek** in 600",
      niet=("Tussenuur",))
wereld(dinsdag(mentor), f"{DI} 15:10")
bevat("tijdens het gesprek", nu(), "### Nu: Mentorgesprek", "Daarna klaar.",
      niet=("Daarna nog",))
wereld(dinsdag(mentor), f"{DI} 16:00")
bevat("na alles: klaar sinds het eind van het gesprek", nu(), "### Klaar sinds 15:30",
      "Volgende schooldag **morgen** om **08:45**")

# ---------------------------------------------------------------------------
# 5. Wat al werkte en zo moet blijven
# ---------------------------------------------------------------------------
wereld(dinsdag(), f"{DI} 11:05")
bevat("tussenuur", nu(), "### Tussenuur tot 11:15", "Daarna **Techniek**", "uit om **14:00**")
wereld(dinsdag(), f"{DI} 09:00")
bevat("bezig + lokaal ontdubbeld", nu(), "### Nu: Lichamelijke opvoeding",
      "lokaal Z2, Z2 gymzaal", "Hierna **Lichamelijke opvoeding** om 09:30, uit om 14:00")
wereld(dinsdag(), f"{DI} 08:35")
bevat("tijdens het coachgesprek", nu(), "### Nu: Coachgesprek Logan",
      "Hierna **Lichamelijke opvoeding** om 08:45")

uitval = les(DI, "12:00", "12:45", "FA", "Frans", is_uitval=True)
wereld(dinsdag(uitval), f"{DI} 07:30")
bevat("vervallen uur apart gemeld", nu(), "**1 uur vervalt vandaag**", "Frans")
bevat("vervallen uur doorgestreept in de tabel", MOD.rooster(KIND, DI), "~~Frans~~ vervalt")

# Zaterdag: vrij, volgende schooldag is maandag. Een boeking op zondag maakt
# van zondag geen schooldag.
ZA = "2026-11-07"
zondag_boeking = afspraak("2026-11-08 10:00:00", "2026-11-08 12:00:00",
                          "10 leerlingen", "", "", "Algemeen", "aula", "boeking")
wereld([zondag_boeking, les("2026-11-09", "08:45", "09:45", "GS", "geschiedenis"),
        les("2026-11-09", "10:00", "11:00", "EN", "Engels")], f"{ZA} 10:00")
gelijk("boeking maakt geen schooldag", MOD.volgende_schooldag(KIND), "2026-11-09")
bevat("vrij vandaag", nu(), "### Vrij vandaag", "om **08:45**",
      "eerste uur Geschiedenis, uit om 11:00")

# ---------------------------------------------------------------------------
# 6. Overzicht van alle kinderen (leest sensor.magister_data)
# ---------------------------------------------------------------------------
wereld(dinsdag(studie, mentor), f"{DI} 07:30")
bevat("overzicht: begin 08:30, tot de laatste les", MOD.overzicht_alle(),
      "**Logan** — school 08:30 tot 14:00")
wereld(dinsdag(studie), f"{DI} 08:35")
bevat("overzicht: afspraak zonder vak heeft een naam", MOD.overzicht_alle(),
      "Coachgesprek Logan tot 08:45")
wereld(dinsdag(studie), f"{DI} 14:05")
bevat("overzicht: boeking houdt hem niet op school", MOD.overzicht_alle(),
      "klaar sinds 14:00")


# ---------------------------------------------------------------------------
# Als pytest dit bestand importeert draait alles hierboven al; deze functie
# geeft pytest alleen iets om te verzamelen.
def test_scenarios():
    assert not FOUTEN, "\n".join(FOUTEN)


if __name__ == "__main__":
    print()
    if FOUTEN:
        print(f"{len(FOUTEN)} FOUT(EN):")
        for f in FOUTEN:
            print("  -", f)
        raise SystemExit(1)
    print("Alle scenario's kloppen.")
