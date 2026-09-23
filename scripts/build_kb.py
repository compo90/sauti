#!/usr/bin/env python3
"""Genere la base de connaissances v1 (~30 questions) + signes de danger enrichis.

TOUT le contenu medical est un SQUELETTE marque [A VALIDER] : formulations
standard (inspirees des recommandations OMS/PCIME) a faire relire et signer par
un professionnel de sante, et a traduire par des locuteurs natifs. Rien ne part
en production sans validation clinique (voir docs/validation_clinique.md).
"""
import json
from pathlib import Path

KB = Path(__file__).resolve().parents[1] / "data" / "knowledge_base"


def rep(fr):
    return {
        "fr":  {"texte": fr, "audio": None, "statut": "traduit"},
        "wol": {"texte": "", "audio": None, "statut": "a_traduire"},
        "ful": {"texte": "", "audio": None, "statut": "a_traduire"},
        "srr": {"texte": "", "audio": None, "statut": "a_traduire"},
    }


def val(ref=""):
    return {"statut": "brouillon", "valide_par": "", "protocole_ref": ref, "date": ""}


def e(id_, intent, secteur, danger, q, fr, ref=""):
    return {"id": id_, "intent": intent, "secteur": secteur, "danger_level": danger,
            "question_source_fr": q, "reponses": rep("[A VALIDER] " + fr), "validation": val(ref)}


faq = [
    # ---------------- PRENATAL ----------------
    e("cpn_frequence", "consultation_prenatale_frequence", "prenatal", "info",
      "Combien de fois dois-je aller a la consultation prenatale ?",
      "L'OMS recommande au moins 8 contacts prenatals. Rendez-vous au poste de sante des que vous "
      "savez que vous etes enceinte, puis suivez le calendrier donne par la sage-femme.", "PNDS a referencer"),
    e("nutrition_grossesse", "nutrition_grossesse", "prenatal", "info",
      "Que dois-je manger pendant la grossesse ?",
      "Mangez varie et prenez chaque jour les comprimes de fer et d'acide folique donnes au poste de sante. "
      "Privilegiez les aliments locaux riches en fer (niebe, feuilles vertes, poisson) et buvez de l'eau propre."),
    e("paludisme_moustiquaire", "prevention_paludisme", "prenatal", "info",
      "Comment me proteger du paludisme enceinte ?",
      "Dormez chaque nuit sous une moustiquaire impregnee et prenez le traitement preventif du paludisme "
      "propose au poste de sante. En cas de fievre, consultez rapidement.", "PNLP"),
    e("vaccin_tetanos", "vaccination_maternelle", "prenatal", "info",
      "Dois-je me faire vacciner pendant la grossesse ?",
      "Oui, le vaccin contre le tetanos protege la mere et le bebe. Suivez les doses indiquees par le poste de sante.", "PEV"),
    e("signes_danger_grossesse", "signes_danger_grossesse", "prenatal", "surveillance",
      "Quels signes doivent m'alerter pendant la grossesse ?",
      "Consultez immediatement en cas de saignement, de fortes douleurs au ventre, de maux de tete violents "
      "avec vision floue, de fievre, de convulsions, ou si le bebe bouge moins que d'habitude."),
    e("nausees_vomissements", "inconforts_grossesse", "prenatal", "info",
      "J'ai des nausees et des vomissements, que faire ?",
      "Mangez en petites quantites et souvent, evitez les odeurs fortes et buvez regulierement. Si les vomissements "
      "sont tres frequents et vous empechent de boire, rendez-vous au poste de sante."),
    e("anemie_fatigue", "anemie_grossesse", "prenatal", "surveillance",
      "Je suis tres fatiguee et pale, est-ce grave ?",
      "La fatigue avec paleur peut signaler une anemie, frequente pendant la grossesse. Continuez le fer/acide folique "
      "et parlez-en au poste de sante pour un controle."),
    e("prise_poids", "suivi_grossesse", "prenatal", "info",
      "Est-ce normal de prendre du poids ?",
      "Oui, prendre du poids progressivement est normal et bon signe. Le poids est suivi a chaque consultation prenatale."),
    e("activite_repos", "mode_de_vie_grossesse", "prenatal", "info",
      "Puis-je continuer a travailler et faire mes taches ?",
      "Une activite moderee est possible, mais menagez-vous, evitez de porter de lourdes charges et reposez-vous. "
      "Ecoutez votre corps."),
    e("tabac_alcool", "mode_de_vie_grossesse", "prenatal", "info",
      "Le tabac et l'alcool sont-ils dangereux enceinte ?",
      "Oui. Evitez le tabac, l'alcool et l'automedication : ils sont nocifs pour le bebe. Ne prenez un medicament "
      "que sur avis d'un soignant."),
    e("tests_cpn", "consultation_prenatale_contenu", "prenatal", "info",
      "Que fait-on lors d'une consultation prenatale ?",
      "On verifie votre tension, votre poids, la croissance du bebe, et on propose des examens utiles (dont le "
      "depistage volontaire). C'est aussi le moment de poser vos questions."),
    e("hygiene_eau", "hygiene_grossesse", "prenatal", "info",
      "Quelles precautions d'hygiene pendant la grossesse ?",
      "Lavez-vous les mains regulierement, buvez de l'eau propre et lavez bien fruits et legumes pour eviter les infections."),

    # ---------------- ACCOUCHEMENT ----------------
    e("preparation_accouchement", "preparation_accouchement", "prenatal", "info",
      "Comment preparer mon accouchement ?",
      "Preparez une trousse (habits, pieces, argent pour le transport), reperez le poste de sante et prevoyez "
      "comment vous y rendre le moment venu. Parlez-en tot avec la sage-femme."),
    e("lieu_accouchement", "lieu_accouchement", "prenatal", "info",
      "Ou dois-je accoucher ?",
      "Accouchez dans une structure de sante avec du personnel qualifie : c'est le plus sur pour vous et le bebe, "
      "et une aide immediate est disponible en cas de complication."),
    e("signes_travail", "signes_travail", "prenatal", "surveillance",
      "Comment savoir que le travail commence ?",
      "Des contractions regulieres et de plus en plus fortes, une perte des eaux ou un bouchon de glaires "
      "annoncent le travail. Rendez-vous au poste de sante."),
    e("signes_danger_accouchement", "signes_danger_accouchement", "prenatal", "urgent",
      "Quels signes de danger pendant le travail ?",
      "Allez immediatement a l'hopital en cas de saignement abondant, de convulsions, de perte de connaissance, "
      "ou si le travail dure tres longtemps sans progresser."),

    # ---------------- POST-PARTUM (MERE) ----------------
    e("saignement_post_partum", "post_partum_saignement", "postnatal", "surveillance",
      "Est-il normal de saigner apres l'accouchement ?",
      "De legeres pertes qui diminuent avec les jours sont normales. Mais un saignement abondant qui trempe "
      "rapidement les protections est une urgence : allez au poste de sante immediatement."),
    e("consultation_postnatale", "consultation_postnatale", "postnatal", "info",
      "Dois-je consulter apres l'accouchement ?",
      "Oui. Une visite postnatale dans les jours qui suivent l'accouchement permet de verifier votre sante et "
      "celle du bebe. Suivez le calendrier donne par le poste de sante."),
    e("planification_familiale", "planification_familiale", "postnatal", "info",
      "Quand puis-je espacer les naissances ?",
      "Espacer les naissances protege votre sante et celle du bebe. Plusieurs methodes existent : demandez conseil "
      "au poste de sante pour choisir celle qui vous convient."),
    e("douleur_seins_allaitement", "allaitement_difficultes", "postnatal", "surveillance",
      "J'ai mal aux seins en allaitant, que faire ?",
      "Continuez a allaiter souvent et videz bien le sein. Si le sein est rouge, dur, chaud et douloureux avec de "
      "la fievre, consultez au poste de sante (risque d'infection)."),
    e("fievre_mere_postpartum", "post_partum_fievre", "postnatal", "urgent",
      "J'ai de la fievre apres l'accouchement, est-ce grave ?",
      "Une fievre apres l'accouchement peut signaler une infection. Rendez-vous au poste de sante sans tarder."),
    e("alimentation_allaitante", "nutrition_postnatale", "postnatal", "info",
      "Que dois-je manger quand j'allaite ?",
      "Mangez varie et a votre faim, buvez suffisamment d'eau propre, et continuez les supplements conseilles par "
      "le poste de sante. Une mere bien nourrie allaite mieux."),

    # ---------------- NOUVEAU-NE ----------------
    e("allaitement_exclusif", "nouveau_ne_allaitement", "nouveau_ne", "info",
      "Dois-je donner de l'eau a mon bebe en plus du lait ?",
      "Jusqu'a 6 mois, l'allaitement maternel exclusif suffit : ni eau, ni autre aliment, sauf avis medical. "
      "Le lait maternel couvre les besoins en eau du bebe."),
    e("allaitement_frequence", "nouveau_ne_allaitement", "nouveau_ne", "info",
      "Combien de fois dois-je allaiter mon bebe ?",
      "Allaitez a la demande, jour et nuit, des que le bebe le reclame (au moins 8 fois par jour). Commencez "
      "l'allaitement dans l'heure qui suit la naissance."),
    e("nouveau_ne_vaccination", "nouveau_ne_vaccination", "nouveau_ne", "info",
      "Quand vacciner mon bebe ?",
      "Suivez le calendrier du Programme Elargi de Vaccination (PEV). Les premiers vaccins commencent a la "
      "naissance. Gardez le carnet de sante et respectez les dates.", "PEV"),
    e("soins_cordon", "nouveau_ne_soins", "nouveau_ne", "surveillance",
      "Comment prendre soin du cordon du bebe ?",
      "Gardez le cordon propre et sec, sans y appliquer de produit. Si la base devient rouge, gonflee, sent mauvais "
      "ou saigne, consultez au poste de sante."),
    e("nouveau_ne_fievre", "nouveau_ne_fievre", "nouveau_ne", "urgent",
      "Mon bebe a de la fievre, que faire ?",
      "Une fievre chez un nouveau-ne peut etre grave. Continuez l'allaitement et rendez-vous au poste de sante "
      "sans tarder. Si le bebe a moins de 2 mois, consultez en urgence."),
    e("ictere_jaunisse", "nouveau_ne_ictere", "nouveau_ne", "surveillance",
      "La peau et les yeux de mon bebe sont jaunes, est-ce grave ?",
      "Une coloration jaune de la peau ou des yeux (jaunisse) doit etre montree rapidement au poste de sante, "
      "surtout si elle apparait tot ou s'accentue."),
    e("garder_bebe_au_chaud", "nouveau_ne_soins", "nouveau_ne", "info",
      "Comment garder mon nouveau-ne au chaud ?",
      "Gardez le bebe contre votre peau (peau a peau), couvrez-lui la tete et evitez les courants d'air. "
      "Le contact peau a peau le rechauffe et favorise l'allaitement."),
    e("signes_danger_nouveau_ne", "signes_danger_nouveau_ne", "nouveau_ne", "urgent",
      "Quels signes de danger chez le nouveau-ne ?",
      "Consultez en urgence si le bebe tete mal ou refuse de teter, respire difficilement, a de la fievre ou est "
      "froid, convulse, est tres mou, ou a le nombril rouge et purulent."),
]

(KB / "faq_maternelle.json").write_text(json.dumps(faq, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------------- Signes de danger : mots-cles FR enrichis (recall) ----------------
danger = json.loads((KB / "signes_danger.json").read_text(encoding="utf-8"))
enrich = {
    "hemorragie": ["saigne", "saignement", "sang", "hemorragie", "perte de sang", "je perds du sang", "sama biir dafa saigne"],
    "convulsions": ["convulsion", "convulse", "crise", "evanoui", "perdu connaissance", "perte de connaissance", "tremble", "tremblement", "raide"],
    "cephalees_vision": ["mal de tete", "maux de tete", "cephalee", "vision floue", "vois flou", "yeux troubles", "trouble de la vue", "tete qui tourne"],
    "fievre_forte": ["fievre", "chaud", "chaleur", "temperature", "brulant", "corps chaud"],
    "mouvements_foetaux": ["bebe ne bouge", "bebe bouge plus", "bouge plus", "pas de mouvement", "bebe immobile", "ne sens plus le bebe"],
    "oedeme": ["gonfle", "gonflement", "enfle", "oedeme", "visage gonfle", "mains gonflees", "pieds gonfles", "jambes gonflees"],
}
for s in danger["signes"]:
    if s["id"] in enrich:
        s["mots_cles"]["fr"] = enrich[s["id"]]
(KB / "signes_danger.json").write_text(json.dumps(danger, ensure_ascii=False, indent=2), encoding="utf-8")

print(f"OK : {len(faq)} entrees FAQ ecrites + mots-cles de danger enrichis.")
