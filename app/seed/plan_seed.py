from __future__ import annotations

from sqlalchemy import select, and_
from sqlalchemy.orm import Session

from app.db.models import ObraSocial, Plan


def _norm(s: str | None) -> str:
    return (s or "").strip()


PLANES = [
        {
            "codigo": "VICTOARTAMB100      ",
            "nombre": "AMBULATORIOS 100%",
            "codigo_obra_social": "VICTORIART          "
        },
        {
            "codigo": "UPR50               ",
            "nombre": "RECETAS 50",
            "codigo_obra_social": "103                 "
        },
        {
            "codigo": "UPR40               ",
            "nombre": "RECETAS 40",
            "codigo_obra_social": "103                 "
        },
        {
            "codigo": "UPR100              ",
            "nombre": "RECETAS 100",
            "codigo_obra_social": "103                 "
        },
        {
            "codigo": "UNIMEDPMI           ",
            "nombre": "PLAN MATERNO INFANTIL",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "UNIMEDPM            ",
            "nombre": "PLAN MATERNO",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "UNIMEDOSVARA50      ",
            "nombre": "OSVARA 50%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "UNIMEDOSVARA40      ",
            "nombre": "OSVARA 40%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "UNIMEDOSSACRA50     ",
            "nombre": "OSSACRA 50%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "UNIMEDOSSACRA40     ",
            "nombre": "OSSACRA 40%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "UNIMEDOSME50        ",
            "nombre": "OSME 50%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "UNIMEDOSME40        ",
            "nombre": "OSME 40%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "UNIMEDOSIM50        ",
            "nombre": "OSIM 50%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "UNIMEDOSIM40        ",
            "nombre": "OSIM 40%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "UNIMEDOSFOT50       ",
            "nombre": "OSFOT 50%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "UNIMEDOSFOT40       ",
            "nombre": "OSFOT 40%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "UNIMEDMIX           ",
            "nombre": "UNIMED MIXTOS",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "UNIMEDCRO           ",
            "nombre": "CRONICOS",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "UNIMEDAUTEST        ",
            "nombre": "UNIMED AUTORIZACIONES ESPECIALES",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "UNIMED50            ",
            "nombre": "UNIMED 50%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "UNIMED40            ",
            "nombre": "UNIMED 40%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "TIRAS               ",
            "nombre": "APROSS TIRAS",
            "codigo_obra_social": "ATI20DEJUN          "
        },
        {
            "codigo": "SWGMANUAL100        ",
            "nombre": "RECETAS MANUALES 100%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SRPAE               ",
            "nombre": "PLAN AUTORIZACIONES ESPECIALES",
            "codigo_obra_social": "SP                  "
        },
        {
            "codigo": "SR50                ",
            "nombre": "PLAN 50%",
            "codigo_obra_social": "SP                  "
        },
        {
            "codigo": "SR50                ",
            "nombre": "PLAN 50%",
            "codigo_obra_social": "SOSSACRA            "
        },
        {
            "codigo": "SR50                ",
            "nombre": "PLAN 50%",
            "codigo_obra_social": "SIPOSACRAV          "
        },
        {
            "codigo": "SR40                ",
            "nombre": "PLAN 40%",
            "codigo_obra_social": "SP                  "
        },
        {
            "codigo": "SR40                ",
            "nombre": "PLAN 40%",
            "codigo_obra_social": "SOSSACRA            "
        },
        {
            "codigo": "SR40                ",
            "nombre": "PLAN 40%",
            "codigo_obra_social": "SIPOSACRAV          "
        },
        {
            "codigo": "SPRPAE              ",
            "nombre": "PLAN AUTORIZACIONES ESPECIALES",
            "codigo_obra_social": "SOSSACRA            "
        },
        {
            "codigo": "SPRPAE              ",
            "nombre": "PLAN AUTORIZACIONES ESPECIALES",
            "codigo_obra_social": "SIPOSACRAV          "
        },
        {
            "codigo": "SOSPOCEPAE          ",
            "nombre": "PLAN AUTORIZACIONES ESPECIALES",
            "codigo_obra_social": "SOSPOCE             "
        },
        {
            "codigo": "SOSPOCE50           ",
            "nombre": "PLAN 50%",
            "codigo_obra_social": "SOSPOCE             "
        },
        {
            "codigo": "SOSPOCE40           ",
            "nombre": "PLAN 40%",
            "codigo_obra_social": "SOSPOCE             "
        },
        {
            "codigo": "SOSIMAPE            ",
            "nombre": "PLAN AUTORIZACIONES ESPECIALES",
            "codigo_obra_social": "SOSIM               "
        },
        {
            "codigo": "SOSIM50             ",
            "nombre": "PLAN 50%",
            "codigo_obra_social": "SOSIM               "
        },
        {
            "codigo": "SOSIM40             ",
            "nombre": "PLAN 40%",
            "codigo_obra_social": "SOSIM               "
        },
        {
            "codigo": "SOPAE               ",
            "nombre": "PLAN AUTORIZACIONES ESPECIALES",
            "codigo_obra_social": "SOSCEP              "
        },
        {
            "codigo": "SOAPAE              ",
            "nombre": "PLAN AUTORIZACIONES ESPECIALES",
            "codigo_obra_social": "SOA                 "
        },
        {
            "codigo": "SOA50               ",
            "nombre": "PLAN 50%",
            "codigo_obra_social": "SOA                 "
        },
        {
            "codigo": "SOA40               ",
            "nombre": "PLAN 40%",
            "codigo_obra_social": "SOA                 "
        },
        {
            "codigo": "SO50                ",
            "nombre": "PLAN 50%",
            "codigo_obra_social": "SOSCEP              "
        },
        {
            "codigo": "SO40                ",
            "nombre": "PLAN 40%",
            "codigo_obra_social": "SOSCEP              "
        },
        {
            "codigo": "SMGTR               ",
            "nombre": "SMG TOTALIDAD DE LAS RECETAS",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMGRG               ",
            "nombre": "SMG RECETAS GENERAL",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMGMANUAL90         ",
            "nombre": "RECETAS MANUALES 90%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMGMANUAL80         ",
            "nombre": "RECETAS MANUALES 80%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMGMANUAL75         ",
            "nombre": "RECETAS MANUALES 75%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMGMANUAL70         ",
            "nombre": "RECETAS MANUALES 70%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMGMANUAL65         ",
            "nombre": "RECETAS MANUALES 65%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMGMANUAL60         ",
            "nombre": "RECETAS MANUALES 60%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMGMANUAL55         ",
            "nombre": "RECETAS MANUALES 55%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMGMANUAL50         ",
            "nombre": "RECETAS MANUALES 50%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMGMANUAL45         ",
            "nombre": "RECETAS MANUALES 45%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMGMANUAL40         ",
            "nombre": "RECETAS MANUALES 40%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMGMANUAL30         ",
            "nombre": "RECETAS MANUALES 30%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMGART100           ",
            "nombre": "AMBULATORIOS 100%",
            "codigo_obra_social": "SMGART              "
        },
        {
            "codigo": "SMG90               ",
            "nombre": "COBERTURA 90%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMG80               ",
            "nombre": "COBERTURA 80%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMG75               ",
            "nombre": "COBERTURA 75%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMG70               ",
            "nombre": "COBERTURA 70%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMG65               ",
            "nombre": "COBERTURA 65%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMG60               ",
            "nombre": "COBERTURA 60%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMG55               ",
            "nombre": "COBERTURA 55%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMG50               ",
            "nombre": "COBERTURA 50%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMG45               ",
            "nombre": "COBERTURA 45%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMG40               ",
            "nombre": "COBERTURA 40%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMG30               ",
            "nombre": "COBERTURA 30%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SMG100              ",
            "nombre": "COBERTURA 100%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "SERVICIOP           ",
            "nombre": "SERVICIO PENITENCIARIO",
            "codigo_obra_social": "SERVP               "
        },
        {
            "codigo": "SERENAART100        ",
            "nombre": "AMBULATORIOS 100%",
            "codigo_obra_social": "SERENAART           "
        },
        {
            "codigo": "SEGARTAMB100        ",
            "nombre": "AMBULATORIOS 100%",
            "codigo_obra_social": "SEGUNDAART          "
        },
        {
            "codigo": "SASSPEPAE           ",
            "nombre": "PLAN AUTORIZACIONES ESPECIALES",
            "codigo_obra_social": "SASSPE              "
        },
        {
            "codigo": "SASSPE50            ",
            "nombre": "PLAN 50%",
            "codigo_obra_social": "SASSPE              "
        },
        {
            "codigo": "SASSPE40            ",
            "nombre": "PLAN 40%",
            "codigo_obra_social": "SASSPE              "
        },
        {
            "codigo": "SAPMPAE             ",
            "nombre": "PLAN AUTORIZACIONES ESPECIALES",
            "codigo_obra_social": "SAPM                "
        },
        {
            "codigo": "SAPM50              ",
            "nombre": "PLAN 50%",
            "codigo_obra_social": "SAPM                "
        },
        {
            "codigo": "SAPM40              ",
            "nombre": "PLAN 40%",
            "codigo_obra_social": "SAPM                "
        },
        {
            "codigo": "SALLENDEPAE         ",
            "nombre": "PLAN AUTORIZACIONES ESPECIALES",
            "codigo_obra_social": "SIPALLENDE          "
        },
        {
            "codigo": "SALLENDEPAE         ",
            "nombre": "PLAN AUTORIZACIONES ESPECIALES",
            "codigo_obra_social": "SIPALLEN36          "
        },
        {
            "codigo": "SALLENDE50          ",
            "nombre": "PLAN 50%",
            "codigo_obra_social": "SIPALLENDE          "
        },
        {
            "codigo": "SALLENDE50          ",
            "nombre": "PLAN 50%",
            "codigo_obra_social": "SIPALLEN36          "
        },
        {
            "codigo": "SALLENDE40          ",
            "nombre": "PLAN 40%",
            "codigo_obra_social": "SIPALLENDE          "
        },
        {
            "codigo": "SALLENDE40          ",
            "nombre": "PLAN 40%",
            "codigo_obra_social": "SIPALLEN36          "
        },
        {
            "codigo": "RSP2                ",
            "nombre": "PLAN 2",
            "codigo_obra_social": "87                  "
        },
        {
            "codigo": "RSP1                ",
            "nombre": "PLAN 1",
            "codigo_obra_social": "87                  "
        },
        {
            "codigo": "REFVALE             ",
            "nombre": "REFACTURADAS",
            "codigo_obra_social": "95                  "
        },
        {
            "codigo": "REFPREVENCION       ",
            "nombre": "REFACTURADAS",
            "codigo_obra_social": "13                  "
        },
        {
            "codigo": "REFACTURADA         ",
            "nombre": "REFACTURADA",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "REFACTURADA         ",
            "nombre": "REFEACTURADAS",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "REFACT              ",
            "nombre": "REFACTURADO",
            "codigo_obra_social": "SEGUNDAART          "
        },
        {
            "codigo": "REFAC               ",
            "nombre": "REFACTURADAS",
            "codigo_obra_social": "87                  "
        },
        {
            "codigo": "REF                 ",
            "nombre": "REFACTURADO",
            "codigo_obra_social": "83                  "
        },
        {
            "codigo": "REF                 ",
            "nombre": "REFACTURADAS",
            "codigo_obra_social": "ANDINAART           "
        },
        {
            "codigo": "REF                 ",
            "nombre": "REFACTURADAS",
            "codigo_obra_social": "OSSACRA             "
        },
        {
            "codigo": "RECTMANUAL70        ",
            "nombre": "RECETAS MANUALES 70%",
            "codigo_obra_social": "26                  "
        },
        {
            "codigo": "PVMM                ",
            "nombre": "VIVIR MEJOR MANUAL",
            "codigo_obra_social": "PAMIMANUAL          "
        },
        {
            "codigo": "PTM                 ",
            "nombre": "PAMI TIRAS MANUAL",
            "codigo_obra_social": "PAMIMANUAL          "
        },
        {
            "codigo": "PT                  ",
            "nombre": "PAMI TIRAS",
            "codigo_obra_social": "80                  "
        },
        {
            "codigo": "PSN                 ",
            "nombre": "PLAN GENERAL",
            "codigo_obra_social": "PAMISUPL            "
        },
        {
            "codigo": "PROVARTAMB          ",
            "nombre": "AMBULATORIOS 100%",
            "codigo_obra_social": "PROVART             "
        },
        {
            "codigo": "PPC                 ",
            "nombre": "PLAN UNIVERSAL",
            "codigo_obra_social": "124                 "
        },
        {
            "codigo": "POLFEDPMI           ",
            "nombre": "PMI",
            "codigo_obra_social": "84                  "
        },
        {
            "codigo": "POLFEDCRO50         ",
            "nombre": "CRONICOS 50%",
            "codigo_obra_social": "84                  "
        },
        {
            "codigo": "POLFEDAMB50         ",
            "nombre": "AMBULATORIOS 50%",
            "codigo_obra_social": "84                  "
        },
        {
            "codigo": "PODJUDAUT           ",
            "nombre": "AUTORIZADAS",
            "codigo_obra_social": "83                  "
        },
        {
            "codigo": "PODJUDAMB           ",
            "nombre": "AMBULATORIO",
            "codigo_obra_social": "83                  "
        },
        {
            "codigo": "PMPN                ",
            "nombre": "PLAN MPN",
            "codigo_obra_social": "MPN                 "
        },
        {
            "codigo": "PMM                 ",
            "nombre": "PAMI MANUAL",
            "codigo_obra_social": "80                  "
        },
        {
            "codigo": "PMI                 ",
            "nombre": "PMI",
            "codigo_obra_social": "18                  "
        },
        {
            "codigo": "PMI                 ",
            "nombre": "PMI",
            "codigo_obra_social": "70                  "
        },
        {
            "codigo": "PMI                 ",
            "nombre": "PMI 100%",
            "codigo_obra_social": "OSETRA              "
        },
        {
            "codigo": "PM9X90              ",
            "nombre": "MODULO 9 X 90",
            "codigo_obra_social": "PM10X30             "
        },
        {
            "codigo": "PM9X30              ",
            "nombre": "MODULO 9 X 30",
            "codigo_obra_social": "PM10X30             "
        },
        {
            "codigo": "PM8X90              ",
            "nombre": "MODULO 8 X 90",
            "codigo_obra_social": "PM10X30             "
        },
        {
            "codigo": "PM8X30              ",
            "nombre": "MODULO 8 X 30",
            "codigo_obra_social": "PM10X30             "
        },
        {
            "codigo": "PM7X90              ",
            "nombre": "MODULO 7 X 90",
            "codigo_obra_social": "PM10X30             "
        },
        {
            "codigo": "PM7X30              ",
            "nombre": "MODULO 7 X 30",
            "codigo_obra_social": "PM10X30             "
        },
        {
            "codigo": "PM6X90              ",
            "nombre": "MODULO 6 X 90",
            "codigo_obra_social": "PM10X30             "
        },
        {
            "codigo": "PM6X30              ",
            "nombre": "MODULO 6 X 30",
            "codigo_obra_social": "PM10X30             "
        },
        {
            "codigo": "PM5X90              ",
            "nombre": "MODULO 5 X 90",
            "codigo_obra_social": "PM10X30             "
        },
        {
            "codigo": "PM5X30              ",
            "nombre": "MODULO 5 X 30",
            "codigo_obra_social": "PM10X30             "
        },
        {
            "codigo": "PM4X90              ",
            "nombre": "MODULO 4 X 90",
            "codigo_obra_social": "PM10X30             "
        },
        {
            "codigo": "PM4X30              ",
            "nombre": "MODULO 4 X 30",
            "codigo_obra_social": "PM10X30             "
        },
        {
            "codigo": "PM3X90              ",
            "nombre": "MODULO 3 X 90",
            "codigo_obra_social": "PM10X30             "
        },
        {
            "codigo": "PM2X90              ",
            "nombre": "MODULO 2 X 90",
            "codigo_obra_social": "PM10X30             "
        },
        {
            "codigo": "PM1X90              ",
            "nombre": "MODULO 1 X90",
            "codigo_obra_social": "PM10X30             "
        },
        {
            "codigo": "PM14X90             ",
            "nombre": "MODULO 14 X 90",
            "codigo_obra_social": "PM10X30             "
        },
        {
            "codigo": "PM12X90             ",
            "nombre": "MODULO 12 X 90",
            "codigo_obra_social": "PM10X30             "
        },
        {
            "codigo": "PM12X30             ",
            "nombre": "MODULO 12 X 30",
            "codigo_obra_social": "PM10X30             "
        },
        {
            "codigo": "PM10X90             ",
            "nombre": "MODULO 10 X 90",
            "codigo_obra_social": "PM10X30             "
        },
        {
            "codigo": "PM10X30             ",
            "nombre": "MODULO 10 X 30",
            "codigo_obra_social": "PM10X30             "
        },
        {
            "codigo": "PLUSART100          ",
            "nombre": "AMBULATORIOS 100%",
            "codigo_obra_social": "PLUSART             "
        },
        {
            "codigo": "PLAN50              ",
            "nombre": "PLAN 50%",
            "codigo_obra_social": "SIPSSAAS            "
        },
        {
            "codigo": "PLAN40              ",
            "nombre": "PLAN 40%",
            "codigo_obra_social": "SIPSSAAS            "
        },
        {
            "codigo": "PLAN1               ",
            "nombre": "PLAN 1",
            "codigo_obra_social": "PLAN1               "
        },
        {
            "codigo": "PLAN MATERNO        ",
            "nombre": "PLAN MATERNO",
            "codigo_obra_social": "18                  "
        },
        {
            "codigo": "PIM                 ",
            "nombre": "PAMI INSULINA MANUAL",
            "codigo_obra_social": "PAMIMANUAL          "
        },
        {
            "codigo": "PI                  ",
            "nombre": "PAMI INSULINAS",
            "codigo_obra_social": "80                  "
        },
        {
            "codigo": "PCM                 ",
            "nombre": "PAMI CRONICOS MANUAL",
            "codigo_obra_social": "PAMIMANUAL          "
        },
        {
            "codigo": "PCI                 ",
            "nombre": "PAMI CRÓNICOS INSULINAS",
            "codigo_obra_social": "80                  "
        },
        {
            "codigo": "PCC                 ",
            "nombre": "PAMI CRÓNICOS CLOZAPINAS",
            "codigo_obra_social": "80                  "
        },
        {
            "codigo": "PC                  ",
            "nombre": "PAMI CRÓNICOS",
            "codigo_obra_social": "80                  "
        },
        {
            "codigo": "PARTM               ",
            "nombre": "MANUALES",
            "codigo_obra_social": "PROVART             "
        },
        {
            "codigo": "PAOM                ",
            "nombre": "ANTIDIABETICOS ORALES MANUAL",
            "codigo_obra_social": "PAMIMANUAL          "
        },
        {
            "codigo": "PAO                 ",
            "nombre": "ANTIDIABETICOS ORALES",
            "codigo_obra_social": "80                  "
        },
        {
            "codigo": "PAMIVIVIRMEJ        ",
            "nombre": "VIVIR MEJOR",
            "codigo_obra_social": "80                  "
        },
        {
            "codigo": "PAMIVACUNAS         ",
            "nombre": "PAMI VACUNAS",
            "codigo_obra_social": "PAMIVACUNA          "
        },
        {
            "codigo": "PAMITDPA            ",
            "nombre": "PAMI TOMA DE PRESION",
            "codigo_obra_social": "PAMITDPA            "
        },
        {
            "codigo": "PAMIOSTOMIA         ",
            "nombre": "PAMI OSTOMIA",
            "codigo_obra_social": "PAMIOSTOMI          "
        },
        {
            "codigo": "PAMIONCO2500        ",
            "nombre": "PLAN 2 ( >= 53900)",
            "codigo_obra_social": "PAMIONCO            "
        },
        {
            "codigo": "PAMIONCO0           ",
            "nombre": "PLAN 1 ( < 53899)",
            "codigo_obra_social": "PAMIONCO            "
        },
        {
            "codigo": "PADBTM              ",
            "nombre": "ACCESORIOS DBT MANUAL",
            "codigo_obra_social": "PAMIMANUAL          "
        },
        {
            "codigo": "PADBT               ",
            "nombre": "ACCESORIOS DBT",
            "codigo_obra_social": "80                  "
        },
        {
            "codigo": "OSVARAMIX           ",
            "nombre": "OSVARA MIXTO",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "OSSACRATR           ",
            "nombre": "OSSACRA TOTALIDAD DE LAS RECETAS",
            "codigo_obra_social": "OSSACRA             "
        },
        {
            "codigo": "OSSACRARG           ",
            "nombre": "OSSACRA RECETAS GENERAL",
            "codigo_obra_social": "OSSACRA             "
        },
        {
            "codigo": "OSSACRAMIX          ",
            "nombre": "OSSACRA MIXTO",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "OSSACRAMANGRAL      ",
            "nombre": "MANUAL GENERAL",
            "codigo_obra_social": "OSSACRA             "
        },
        {
            "codigo": "OSSACRAMAN70        ",
            "nombre": "MANUAL 70%",
            "codigo_obra_social": "OSSACRA             "
        },
        {
            "codigo": "OSSACRAMAN40        ",
            "nombre": "MANUAL 40%",
            "codigo_obra_social": "OSSACRA             "
        },
        {
            "codigo": "OSSACRAMAN100       ",
            "nombre": "MANUAL 100%",
            "codigo_obra_social": "OSSACRA             "
        },
        {
            "codigo": "OSSACRA40           ",
            "nombre": "COBERTURA 40%",
            "codigo_obra_social": "OSSACRA             "
        },
        {
            "codigo": "OSSACRA100          ",
            "nombre": "COBERTURA 100%",
            "codigo_obra_social": "OSSACRA             "
        },
        {
            "codigo": "OSPPRA              ",
            "nombre": "OSPPRA",
            "codigo_obra_social": "OSPRPA              "
        },
        {
            "codigo": "OSPJNTR             ",
            "nombre": "OSPJN TOTALIDAD RECETAS",
            "codigo_obra_social": "OSPJN               "
        },
        {
            "codigo": "OSPJNRG             ",
            "nombre": "OSPJN RECETAS GENERAL",
            "codigo_obra_social": "OSPJN               "
        },
        {
            "codigo": "OSPJNREF            ",
            "nombre": "REFACTURADAS",
            "codigo_obra_social": "OSPJN               "
        },
        {
            "codigo": "OSPJNMAN70          ",
            "nombre": "MANUAL 70%",
            "codigo_obra_social": "OSPJN               "
        },
        {
            "codigo": "OSPJNAUT            ",
            "nombre": "AUTORIZADAS",
            "codigo_obra_social": "OSPJN               "
        },
        {
            "codigo": "OSPJNAMB            ",
            "nombre": "AMBULATORIOS",
            "codigo_obra_social": "OSPJN               "
        },
        {
            "codigo": "OSPJMAN100          ",
            "nombre": "MANUAL 100%",
            "codigo_obra_social": "OSPJN               "
        },
        {
            "codigo": "OSPIPMIX            ",
            "nombre": "MIXTO",
            "codigo_obra_social": "70                  "
        },
        {
            "codigo": "OSPIPAUT100         ",
            "nombre": "AUTORIZADOS 100%",
            "codigo_obra_social": "70                  "
        },
        {
            "codigo": "OSPIPAMBCOS         ",
            "nombre": "AMBU C/COSEGURO",
            "codigo_obra_social": "70                  "
        },
        {
            "codigo": "OSPIPA100           ",
            "nombre": "AUTORIZADOS 70%",
            "codigo_obra_social": "70                  "
        },
        {
            "codigo": "OSPIPA              ",
            "nombre": "AMBULATORIO",
            "codigo_obra_social": "70                  "
        },
        {
            "codigo": "OSPILAUT50          ",
            "nombre": "OSPIL AUTORIZADAS 50%",
            "codigo_obra_social": "68                  "
        },
        {
            "codigo": "OSPILAUT100         ",
            "nombre": "OSPIL AUTORIZADAS 100%",
            "codigo_obra_social": "68                  "
        },
        {
            "codigo": "OSPILAMPIL          ",
            "nombre": "OSPIL-AMPIL",
            "codigo_obra_social": "68                  "
        },
        {
            "codigo": "OSPICALPMI          ",
            "nombre": "PMI",
            "codigo_obra_social": "249                 "
        },
        {
            "codigo": "OSPICALDISCAP       ",
            "nombre": "DISCAPACIDAD",
            "codigo_obra_social": "249                 "
        },
        {
            "codigo": "OSPICALCRONI        ",
            "nombre": "CRONICOS",
            "codigo_obra_social": "249                 "
        },
        {
            "codigo": "OSPICALAUT          ",
            "nombre": "AUTORIZADO",
            "codigo_obra_social": "249                 "
        },
        {
            "codigo": "OSPFINTAUT          ",
            "nombre": "INTERNACION AUTORIZADOS",
            "codigo_obra_social": "66                  "
        },
        {
            "codigo": "OSPFAMBMIX          ",
            "nombre": "AMBULATORIO MIXTO",
            "codigo_obra_social": "66                  "
        },
        {
            "codigo": "OSPAJMAN40          ",
            "nombre": "MANUAL 40%",
            "codigo_obra_social": "OSPJN               "
        },
        {
            "codigo": "OSPACAPMI           ",
            "nombre": "PMI 100%",
            "codigo_obra_social": "60                  "
        },
        {
            "codigo": "OSPACADISAUT        ",
            "nombre": "DISCAPACIDADES/AUTORIZADOS",
            "codigo_obra_social": "60                  "
        },
        {
            "codigo": "OSPACACRO           ",
            "nombre": "CRONICOS",
            "codigo_obra_social": "60                  "
        },
        {
            "codigo": "OSPACAAMB40         ",
            "nombre": "AMBULATORIOS 40%",
            "codigo_obra_social": "60                  "
        },
        {
            "codigo": "OSMEMIX             ",
            "nombre": "OSME MIXTO",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "OSMATAVARIOS        ",
            "nombre": "VARIOS",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "OSMATAPMI100        ",
            "nombre": "PMI 100%",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "OSMATAOBLIGA40      ",
            "nombre": "OBLIGATORIO 40%",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "OSMATAMATERNO       ",
            "nombre": "PLAN MATERNO",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "OSMATALECHES        ",
            "nombre": "LECHES MEDICAMENTOSAS",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "OSMATAINTEG50       ",
            "nombre": "INTEGRAL 50%",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "OSMATAINSULINAS     ",
            "nombre": "PLAN INSULINAS",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "OSMATACRON70100     ",
            "nombre": "CRONICOS 70%-100%",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "OSMATAAMBMIX        ",
            "nombre": "AMBULATORIOS MIXTOS",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "OSIMMIX             ",
            "nombre": "OSIM MIXTOS",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "OSIAOIPMI           ",
            "nombre": "PMI",
            "codigo_obra_social": "OSIAOIT             "
        },
        {
            "codigo": "OSIAOIJUB           ",
            "nombre": "JUBILADOS",
            "codigo_obra_social": "OSIAOIT             "
        },
        {
            "codigo": "OSIAOIAMB           ",
            "nombre": "AMBULATORIOS",
            "codigo_obra_social": "OSIAOIT             "
        },
        {
            "codigo": "OSFOTMIX            ",
            "nombre": "OSFOT MIXTOS",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "OSFATLYGCROBAS70    ",
            "nombre": "CRONICOS BASICO (70%)",
            "codigo_obra_social": "43                  "
        },
        {
            "codigo": "OSFATLYFVARIO       ",
            "nombre": "OSFATLYF VARIOS",
            "codigo_obra_social": "43                  "
        },
        {
            "codigo": "OSFATLYFPMOB4070100 ",
            "nombre": "PMO BASICO 40% (70% Y 100%)",
            "codigo_obra_social": "43                  "
        },
        {
            "codigo": "OSFATLYFPM100       ",
            "nombre": "PLAN MATERNO 100%",
            "codigo_obra_social": "43                  "
        },
        {
            "codigo": "OSFATLYFAUTO        ",
            "nombre": "AUTORIZADAS",
            "codigo_obra_social": "43                  "
        },
        {
            "codigo": "OSFATLYFANTICON100  ",
            "nombre": "ANTICONCEPTIVOS 100%",
            "codigo_obra_social": "43                  "
        },
        {
            "codigo": "OSETRAMBU           ",
            "nombre": "OSETRA AMBULATORIO 60%",
            "codigo_obra_social": "OSETRA              "
        },
        {
            "codigo": "OSETRACRONIC        ",
            "nombre": "OSETRA CRONICOS 70%",
            "codigo_obra_social": "OSETRA              "
        },
        {
            "codigo": "OSETRAAUT           ",
            "nombre": "OSETRA AUTORIZADAS",
            "codigo_obra_social": "OSETRA              "
        },
        {
            "codigo": "OSEFESPECIAL        ",
            "nombre": "ESPECIALES",
            "codigo_obra_social": "OSEF                "
        },
        {
            "codigo": "OSEFAMBU            ",
            "nombre": "AMBULATORIO",
            "codigo_obra_social": "OSEF                "
        },
        {
            "codigo": "OSADEFREF           ",
            "nombre": "REFACTURADAS",
            "codigo_obra_social": "OSADEF              "
        },
        {
            "codigo": "OSADEFPMI           ",
            "nombre": "PMI",
            "codigo_obra_social": "OSADEF              "
        },
        {
            "codigo": "OSADEFAUTORIZADO    ",
            "nombre": "AUTORIZADO",
            "codigo_obra_social": "OSADEF              "
        },
        {
            "codigo": "OSADEFAMB           ",
            "nombre": "AMBULATORIO",
            "codigo_obra_social": "OSADEF              "
        },
        {
            "codigo": "OPSAMBU             ",
            "nombre": "AMBULATORIO",
            "codigo_obra_social": "249                 "
        },
        {
            "codigo": "OPDEATR             ",
            "nombre": "OPDEA TOTALIDAD RECETAS",
            "codigo_obra_social": "OPDEA               "
        },
        {
            "codigo": "OPDEARG             ",
            "nombre": "OPDEA RECETAS GENERAL",
            "codigo_obra_social": "OPDEA               "
        },
        {
            "codigo": "OPDEAMANUAL70       ",
            "nombre": "RECETAS MANUALES 70%",
            "codigo_obra_social": "OPDEA               "
        },
        {
            "codigo": "OPDEAMANUAL40       ",
            "nombre": "RECETAS MANUALES 40%",
            "codigo_obra_social": "OPDEA               "
        },
        {
            "codigo": "OPDEAMANUAL100      ",
            "nombre": "RECETAS MANUALES 100%",
            "codigo_obra_social": "OPDEA               "
        },
        {
            "codigo": "OPDEA40             ",
            "nombre": "RECETAS 40",
            "codigo_obra_social": "OPDEA               "
        },
        {
            "codigo": "OPDEA100            ",
            "nombre": "RECETAS 100",
            "codigo_obra_social": "OPDEA               "
        },
        {
            "codigo": "OMINTTR             ",
            "nombre": "OMINT TOTALIDAD RECETAS",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "OMINTRG             ",
            "nombre": "OMINT RECETAS GENERAL",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "OMINTMANUAL80       ",
            "nombre": "RECETAS MANUALES 80%",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "OMINTMANUAL75       ",
            "nombre": "RECETAS MANUALES 75%",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "OMINTMANUAL70       ",
            "nombre": "RECETAS MANUALES 70%",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "OMINTMANUAL65       ",
            "nombre": "RECETAS MANUALES 65%",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "OMINTMANUAL60       ",
            "nombre": "RECETAS MANUALES 60%",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "OMINTMANUAL55       ",
            "nombre": "RECETAS MANUALES 55%",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "OMINTMANUAL50       ",
            "nombre": "RECETAS MANUALES 50%",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "OMINTMANUAL40       ",
            "nombre": "RECETAS MANUALES 40%",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "OMINTMANUAL100      ",
            "nombre": "RECETAS MANUALES 100%",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "OMINTAUTORIZADAS    ",
            "nombre": "AUTORIZADAS",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "OMINTAMBDI          ",
            "nombre": "OMINT DIABETICOS AMBULATORIO",
            "codigo_obra_social": "OMINTDIAB           "
        },
        {
            "codigo": "OMINT80             ",
            "nombre": "COBERTURA 80%",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "OMINT75             ",
            "nombre": "COBERTURA 75%",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "OMINT70             ",
            "nombre": "COBERTURA 70%",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "OMINT60             ",
            "nombre": "COBERTURA 60%",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "OMINT55             ",
            "nombre": "COBERTURA 55%",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "OMINT50             ",
            "nombre": "COBERTURA 50%",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "OMINT40             ",
            "nombre": "COBERTURA 40%",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "OMINT100            ",
            "nombre": "COBERTURA 100%",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "MUE                 ",
            "nombre": "MEDICAMENTOS DE USO EVENTUAL",
            "codigo_obra_social": "80                  "
        },
        {
            "codigo": "MPNREF              ",
            "nombre": "MPN REFACTURADAS",
            "codigo_obra_social": "MPN                 "
        },
        {
            "codigo": "MPNJ                ",
            "nombre": "PLAN J",
            "codigo_obra_social": "MPN                 "
        },
        {
            "codigo": "MPNCB               ",
            "nombre": "PLAN CB",
            "codigo_obra_social": "MPN                 "
        },
        {
            "codigo": "MPNA                ",
            "nombre": "PLAN A",
            "codigo_obra_social": "MPN                 "
        },
        {
            "codigo": "MFSTR               ",
            "nombre": "MFS TOTALIDAD DE LAS RECETAS",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "MFSRG               ",
            "nombre": "MFS RECETAS GENERAL",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "MERIDIONALARTAMB100 ",
            "nombre": "AMBULATORIOS 100%",
            "codigo_obra_social": "MERIDIOART          "
        },
        {
            "codigo": "MEBACOSEGURO        ",
            "nombre": "COSEGURO",
            "codigo_obra_social": "MEBA                "
        },
        {
            "codigo": "MEBAAMB100          ",
            "nombre": "AMBULATORIOS 100%",
            "codigo_obra_social": "MEBA                "
        },
        {
            "codigo": "MANUAL              ",
            "nombre": "MANUALES",
            "codigo_obra_social": "70                  "
        },
        {
            "codigo": "MACAMB50            ",
            "nombre": "AMBULATORIOS 50%",
            "codigo_obra_social": "MAC                 "
        },
        {
            "codigo": "MACAMB40            ",
            "nombre": "AMBULATORIOS 40%",
            "codigo_obra_social": "MAC                 "
        },
        {
            "codigo": "LYFPMOESP4070100    ",
            "nombre": "PMO ESPECIAL 40%(70% Y 100%)",
            "codigo_obra_social": "43                  "
        },
        {
            "codigo": "LYFPMI100           ",
            "nombre": "PLAN MATERNO INFANTIL 100%",
            "codigo_obra_social": "43                  "
        },
        {
            "codigo": "LYFCROESP70         ",
            "nombre": "CRONICOS ESPECIAL (70%)",
            "codigo_obra_social": "43                  "
        },
        {
            "codigo": "LYFANTICON          ",
            "nombre": "ANTICONCEPTIVOS PMO 100% Y 40%",
            "codigo_obra_social": "43                  "
        },
        {
            "codigo": "LYFAMBMIX           ",
            "nombre": "AMBULATORIOS MIXTOS",
            "codigo_obra_social": "43                  "
        },
        {
            "codigo": "LIC25-28            ",
            "nombre": "LICITACION 25 Y 28",
            "codigo_obra_social": "PAMIONCO            "
        },
        {
            "codigo": "LIC                 ",
            "nombre": "LICITACION 11-18-28-78 Y 80",
            "codigo_obra_social": "PAMIONCO            "
        },
        {
            "codigo": "LA100               ",
            "nombre": "AMBULATORIOS 100%",
            "codigo_obra_social": "LIDERAR             "
        },
        {
            "codigo": "JEREF               ",
            "nombre": "REFACTURADAS",
            "codigo_obra_social": "42                  "
        },
        {
            "codigo": "JERARAMB            ",
            "nombre": "AMBULATORIOS",
            "codigo_obra_social": "42                  "
        },
        {
            "codigo": "INTERNACION         ",
            "nombre": "INTERNACION",
            "codigo_obra_social": "18                  "
        },
        {
            "codigo": "INSULINAS           ",
            "nombre": "APROSS INSULINAS",
            "codigo_obra_social": "ATI20DEJUN          "
        },
        {
            "codigo": "IBEROASISTAMB       ",
            "nombre": "AMBULATORIOS 100%",
            "codigo_obra_social": "IBEROASIST          "
        },
        {
            "codigo": "HPCBA               ",
            "nombre": "GENERAL ONLINE",
            "codigo_obra_social": "HPCBA               "
        },
        {
            "codigo": "GENERAL 100%        ",
            "nombre": "GENERAL",
            "codigo_obra_social": "MUTRALART           "
        },
        {
            "codigo": "GELENORC            ",
            "nombre": "GALENO RECETAS GENERAL",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GALENOTR            ",
            "nombre": "GALENO TOTALIDAD RECETAS",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GALENOMANUAL85      ",
            "nombre": "RECETAS MANUALES 85%",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GALENOMANUAL80      ",
            "nombre": "RECETAS MANUALES 80%",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GALENOMANUAL75      ",
            "nombre": "RECETAS MANUALES 75%",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GALENOMANUAL70      ",
            "nombre": "RECETAS MANUALES 70%",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GALENOMANUAL65      ",
            "nombre": "RECETAS MANUALES 65%",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GALENOMANUAL60      ",
            "nombre": "RECETAS MANUALES 60%",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GALENOMANUAL55      ",
            "nombre": "RECETAS MANUALES 55%",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GALENOMANUAL50      ",
            "nombre": "RECETAS MANUALES 50%",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GALENOMANUAL45      ",
            "nombre": "RECETAS MANUALES 45%",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GALENOMANUAL40      ",
            "nombre": "RECETAS MANUALES 40%",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GALENOMANUAL100     ",
            "nombre": "RECETAS MANUALES 100%",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GALENOART100        ",
            "nombre": "AMBULATORIOS 100%",
            "codigo_obra_social": "GALENOART           "
        },
        {
            "codigo": "GALENO              ",
            "nombre": "REFACTURADO",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GAL85               ",
            "nombre": "COBERTURA 85%",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GAL80               ",
            "nombre": "COBERTURA 80%",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GAL75               ",
            "nombre": "COBERTURA 75%",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GAL70               ",
            "nombre": "COBERTURA 70%",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GAL65               ",
            "nombre": "COBERTURA 65%",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GAL60               ",
            "nombre": "COBERTURA 60%",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GAL55               ",
            "nombre": "COBERTURA 55%",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GAL50               ",
            "nombre": "COBERTURA 50%",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GAL45               ",
            "nombre": "COBERTURA 45%",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GAL40               ",
            "nombre": "COBERTURA 40%",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "GAL100              ",
            "nombre": "COBERTURA 100%",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "FEDSALMANUAL80      ",
            "nombre": "RECETAS MANUALES 80%",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "FEDSALMANUAL75      ",
            "nombre": "RECETAS MANUALES 75%",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "FEDSALMANUAL70      ",
            "nombre": "RECETAS MANUALES 70%",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "FEDSALMANUAL60      ",
            "nombre": "RECETAS MANUALES 60%",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "FEDSALMANUAL55      ",
            "nombre": "RECETAS MANUALES 55%",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "FEDSALMANUAL50      ",
            "nombre": "RECETAS MANUALES 50%",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "FEDSALMANUAL40      ",
            "nombre": "RECETAS MANUALES 40%",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "FEDSALMANUAL100     ",
            "nombre": "RECETAS MANUALES 100%",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "FEDSAL80            ",
            "nombre": "AMBULATORIOS 80%",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "FEDSAL75            ",
            "nombre": "AMBULATORIOS 75%",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "FEDSAL70            ",
            "nombre": "AMBULATORIOS 70%",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "FEDSAL60            ",
            "nombre": "AMBULATORIOS 60%",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "FEDSAL55            ",
            "nombre": "AMBULATORIOS 55%",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "FEDSAL50            ",
            "nombre": "AMBULATORIOS 50%",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "FEDSAL40            ",
            "nombre": "AMBULATORIOS 40%",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "FEDSAL100           ",
            "nombre": "AMBULATORIOS 100%",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "EXPARTAMB100        ",
            "nombre": "AMBULATORIOS 100%",
            "codigo_obra_social": "EXPART              "
        },
        {
            "codigo": "EARTA100            ",
            "nombre": "AMBULATORIOS 100%",
            "codigo_obra_social": "EA                  "
        },
        {
            "codigo": "DASVAC              ",
            "nombre": "VACUNAS",
            "codigo_obra_social": "DASUTEN             "
        },
        {
            "codigo": "DASUTENANTCON       ",
            "nombre": "ANTICONCEPTIVOS",
            "codigo_obra_social": "DASUTEN             "
        },
        {
            "codigo": "DASUTENAMBMIX       ",
            "nombre": "AMBULATORIOS MIXTOS",
            "codigo_obra_social": "DASUTEN             "
        },
        {
            "codigo": "DASUTENACCTRA       ",
            "nombre": "ACCIDENTES DE TRABAJO",
            "codigo_obra_social": "DASUTEN             "
        },
        {
            "codigo": "DAREF               ",
            "nombre": "REFACUTURADAS",
            "codigo_obra_social": "DASUTEN             "
        },
        {
            "codigo": "CSSAMB100           ",
            "nombre": "AMBULATORIO 100%",
            "codigo_obra_social": "23                  "
        },
        {
            "codigo": "CPCETR              ",
            "nombre": "CPCE TOTALIDAD DE LAS RECETAS",
            "codigo_obra_social": "26                  "
        },
        {
            "codigo": "CPCERG              ",
            "nombre": "CPCE RECETAS GENERAL",
            "codigo_obra_social": "26                  "
        },
        {
            "codigo": "CPCEMANUAL50        ",
            "nombre": "RECETAS MANUALES 50%",
            "codigo_obra_social": "26                  "
        },
        {
            "codigo": "CPCEMANUAL40        ",
            "nombre": "RECETAS MANUALES 40%",
            "codigo_obra_social": "26                  "
        },
        {
            "codigo": "CPCEMANUAL100       ",
            "nombre": "RECETAS MANUALES 100%",
            "codigo_obra_social": "26                  "
        },
        {
            "codigo": "CPCE70              ",
            "nombre": "COBERTURA 70%",
            "codigo_obra_social": "26                  "
        },
        {
            "codigo": "CPCE50              ",
            "nombre": "COBERTURA 50%",
            "codigo_obra_social": "26                  "
        },
        {
            "codigo": "CPCE100             ",
            "nombre": "COBERTURA 100%",
            "codigo_obra_social": "26                  "
        },
        {
            "codigo": "CJNODBT             ",
            "nombre": "DIABETES",
            "codigo_obra_social": "18                  "
        },
        {
            "codigo": "CEASP40             ",
            "nombre": "RECETAS 40%",
            "codigo_obra_social": "CEASANPEDR          "
        },
        {
            "codigo": "CAMPROART100        ",
            "nombre": "AMBULATORIOS 100%",
            "codigo_obra_social": "CAMPROART           "
        },
        {
            "codigo": "AUTESP              ",
            "nombre": "AUTORIZACIONES ESPECIALES",
            "codigo_obra_social": "43                  "
        },
        {
            "codigo": "AUTESP              ",
            "nombre": "AUTORIZACIONES ESPECIALES",
            "codigo_obra_social": "SIPSSAAS            "
        },
        {
            "codigo": "AUT100              ",
            "nombre": "AUTORIZADAS 100%",
            "codigo_obra_social": "ANDINAART           "
        },
        {
            "codigo": "AT                  ",
            "nombre": "APROSS TIRAS",
            "codigo_obra_social": "12                  "
        },
        {
            "codigo": "ASOARTREF           ",
            "nombre": "REFACTURADAS",
            "codigo_obra_social": "ASOCIARTAR          "
        },
        {
            "codigo": "ASOARTAMB           ",
            "nombre": "AMBULATORIOS 100%",
            "codigo_obra_social": "ASOCIARTAR          "
        },
        {
            "codigo": "AR120R              ",
            "nombre": "APROSS RESOLUCION 120(RES)",
            "codigo_obra_social": "12                  "
        },
        {
            "codigo": "AR120               ",
            "nombre": "APROSS RESOLUCION 120",
            "codigo_obra_social": "12                  "
        },
        {
            "codigo": "APTIR               ",
            "nombre": "APROSS TIRAS",
            "codigo_obra_social": "APROSSINS           "
        },
        {
            "codigo": "APTIR               ",
            "nombre": "APROSS TIRAS",
            "codigo_obra_social": "APROSSDOCU          "
        },
        {
            "codigo": "APROSSTIRAS         ",
            "nombre": "APROSS TIRAS",
            "codigo_obra_social": "ATEISUIZO           "
        },
        {
            "codigo": "APROSSONCO175       ",
            "nombre": "FARMALIVE 197",
            "codigo_obra_social": "APROSSONCO          "
        },
        {
            "codigo": "APROSSMETA          ",
            "nombre": "APROSS TIRAS META",
            "codigo_obra_social": "APROSSMETA          "
        },
        {
            "codigo": "APROSSINSU          ",
            "nombre": "APROSS INSULINAS",
            "codigo_obra_social": "ATEISUIZO           "
        },
        {
            "codigo": "APOSMANUAL          ",
            "nombre": "APOSMANUAL",
            "codigo_obra_social": "APOS                "
        },
        {
            "codigo": "APOSGRAL            ",
            "nombre": "GENERAL ONLINE",
            "codigo_obra_social": "APOS                "
        },
        {
            "codigo": "APMTIR              ",
            "nombre": "APROSS MIXTA TIRAS",
            "codigo_obra_social": "APROSSINS           "
        },
        {
            "codigo": "APMREF              ",
            "nombre": "APM REFACTURADAS",
            "codigo_obra_social": "11                  "
        },
        {
            "codigo": "APMIXT              ",
            "nombre": "APROSS MIXTA TIRAS",
            "codigo_obra_social": "APROSSDOCU          "
        },
        {
            "codigo": "APMIX               ",
            "nombre": "APROSS MIXTA INSULINAS",
            "codigo_obra_social": "APROSSDOCU          "
        },
        {
            "codigo": "APMINS              ",
            "nombre": "APROSS MIXTA INSULINAS",
            "codigo_obra_social": "APROSSINS           "
        },
        {
            "codigo": "APINSREF            ",
            "nombre": "APROSS REFACTURADAS",
            "codigo_obra_social": "APROSSINS           "
        },
        {
            "codigo": "APINS               ",
            "nombre": "APROSS INSULINAS",
            "codigo_obra_social": "APROSSINS           "
        },
        {
            "codigo": "APINS               ",
            "nombre": "APROSS INSULINAS",
            "codigo_obra_social": "APROSSDOCU          "
        },
        {
            "codigo": "ANTICONCEPTIVOS     ",
            "nombre": "ANTICONCEPTIVOS",
            "codigo_obra_social": "18                  "
        },
        {
            "codigo": "AMT                 ",
            "nombre": "APROSS MIXTA TIRAS",
            "codigo_obra_social": "12                  "
        },
        {
            "codigo": "AMPILAMB20          ",
            "nombre": "AMBULATORIOS AMPIL 20%",
            "codigo_obra_social": "AMPIL               "
        },
        {
            "codigo": "AMI                 ",
            "nombre": "APROSS MIXTA INSULINAS",
            "codigo_obra_social": "12                  "
        },
        {
            "codigo": "AMBU60              ",
            "nombre": "ABULATORIO 60%",
            "codigo_obra_social": "70                  "
        },
        {
            "codigo": "ACO                 ",
            "nombre": "ANTICONCEPTIVOS",
            "codigo_obra_social": "70                  "
        },
        {
            "codigo": "ABU40               ",
            "nombre": "AMBULATORIO 40",
            "codigo_obra_social": "70                  "
        },
        {
            "codigo": "AAMP                ",
            "nombre": "APROSS AMPARO",
            "codigo_obra_social": "12                  "
        },
        {
            "codigo": "AAM                 ",
            "nombre": "APROSS AMBULATORIO MANUAL",
            "codigo_obra_social": "12                  "
        },
        {
            "codigo": "1852                ",
            "nombre": "OSPPCYQ AMBULATORIO",
            "codigo_obra_social": "105                 "
        },
        {
            "codigo": "1851                ",
            "nombre": "CORDOBA CON ELLAS",
            "codigo_obra_social": "102                 "
        },
        {
            "codigo": "1850                ",
            "nombre": "MUTUAL FEDERADA AMBULATORIO",
            "codigo_obra_social": "101                 "
        },
        {
            "codigo": "1849                ",
            "nombre": "PREVENCION SALUD AMBULATORIO",
            "codigo_obra_social": "13                  "
        },
        {
            "codigo": "1848                ",
            "nombre": "COOPERAT HORIZONTE PERFUMERIA",
            "codigo_obra_social": "98                  "
        },
        {
            "codigo": "1847                ",
            "nombre": "OSADRA 100% ESPECIAL",
            "codigo_obra_social": "49                  "
        },
        {
            "codigo": "1846                ",
            "nombre": "OSADRA  70% ESPECIAL",
            "codigo_obra_social": "49                  "
        },
        {
            "codigo": "1845                ",
            "nombre": "OSPAGA COB.ESPECIALES",
            "codigo_obra_social": "96                  "
        },
        {
            "codigo": "1844                ",
            "nombre": "OSPAGA CRONICIDAD",
            "codigo_obra_social": "96                  "
        },
        {
            "codigo": "1842                ",
            "nombre": "ENSALUD ANTICONCEPTIVOS",
            "codigo_obra_social": "94                  "
        },
        {
            "codigo": "1841                ",
            "nombre": "ENSALUD PMI",
            "codigo_obra_social": "94                  "
        },
        {
            "codigo": "1840                ",
            "nombre": "ENSALUD CRONICIDAD",
            "codigo_obra_social": "94                  "
        },
        {
            "codigo": "1839                ",
            "nombre": "ENSALUD AMBULATORIO",
            "codigo_obra_social": "94                  "
        },
        {
            "codigo": "1838                ",
            "nombre": "IOSE VACUNAS",
            "codigo_obra_social": "40                  "
        },
        {
            "codigo": "1837                ",
            "nombre": "IOSE PMI",
            "codigo_obra_social": "40                  "
        },
        {
            "codigo": "1836                ",
            "nombre": "IOSE CONTRACEPCION",
            "codigo_obra_social": "40                  "
        },
        {
            "codigo": "1835                ",
            "nombre": "DIBA VACUNAS",
            "codigo_obra_social": "29                  "
        },
        {
            "codigo": "1834                ",
            "nombre": "DIBA PMI",
            "codigo_obra_social": "29                  "
        },
        {
            "codigo": "1833                ",
            "nombre": "DIBA CONTRACEPCION",
            "codigo_obra_social": "29                  "
        },
        {
            "codigo": "1832                ",
            "nombre": "DIBPFA CONTRACEPCION",
            "codigo_obra_social": "30                  "
        },
        {
            "codigo": "1831                ",
            "nombre": "DIBPFA ACTA  90%              ",
            "codigo_obra_social": "30                  "
        },
        {
            "codigo": "1830                ",
            "nombre": "BOREAL PLAN MAGNUM",
            "codigo_obra_social": "97                  "
        },
        {
            "codigo": "1829                ",
            "nombre": "BOREAL PLAN GENUINOS",
            "codigo_obra_social": "97                  "
        },
        {
            "codigo": "1828                ",
            "nombre": "BOREAL PLAN PMOE",
            "codigo_obra_social": "97                  "
        },
        {
            "codigo": "1827                ",
            "nombre": "BOREAL PLAN PMO-OSIMRA",
            "codigo_obra_social": "97                  "
        },
        {
            "codigo": "1826                ",
            "nombre": "BOREAL PLAN PMO",
            "codigo_obra_social": "97                  "
        },
        {
            "codigo": "1825                ",
            "nombre": "BOREAL PLAN M2",
            "codigo_obra_social": "97                  "
        },
        {
            "codigo": "1824                ",
            "nombre": "BOREAL PLAN M1",
            "codigo_obra_social": "97                  "
        },
        {
            "codigo": "1823                ",
            "nombre": "BOREAL PLAN CLASICO",
            "codigo_obra_social": "97                  "
        },
        {
            "codigo": "1822                ",
            "nombre": "BOREAL PLAN BASICO",
            "codigo_obra_social": "97                  "
        },
        {
            "codigo": "1821                ",
            "nombre": "BOREAL PLAN EXT.DE COBERT.",
            "codigo_obra_social": "97                  "
        },
        {
            "codigo": "1820                ",
            "nombre": "BOREAL PLAN SUBS DESEMPLEO",
            "codigo_obra_social": "97                  "
        },
        {
            "codigo": "1819                ",
            "nombre": "BOREAL PLAN PMI",
            "codigo_obra_social": "97                  "
        },
        {
            "codigo": "1816                ",
            "nombre": "BOREAL PLAN A3",
            "codigo_obra_social": "97                  "
        },
        {
            "codigo": "1815                ",
            "nombre": "BOREAL PLAN A2",
            "codigo_obra_social": "97                  "
        },
        {
            "codigo": "1814                ",
            "nombre": "COOPERAT HORIZONTE AMBULATORIO",
            "codigo_obra_social": "98                  "
        },
        {
            "codigo": "1813                ",
            "nombre": "OSPRERA AMB MONOTRIBUTISTA    ",
            "codigo_obra_social": "74                  "
        },
        {
            "codigo": "1812                ",
            "nombre": "OMINT PLAN Y6-LINEA JOHN DEER",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "1811                ",
            "nombre": "OMINT PLAN YC-LINEA YC",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "1810                ",
            "nombre": "OMINT PLAN Y-LINEA Y",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "1809                ",
            "nombre": "OMINT PLAN XO-NEXTEL LINEA O",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "1808                ",
            "nombre": "OMINT PLAN XF-NEXTEL LINEA F",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "1807                ",
            "nombre": "OMINT PLAN XEC-NEXTEL SKILL PL",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "1806                ",
            "nombre": "OMINT PLAN XE-NEXTEL SKILL PLU",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "1805                ",
            "nombre": "OMINT PLAN VC-LINEA VC",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "1804                ",
            "nombre": "OMINT PLAN R-LINEA RENAULT",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "1803                ",
            "nombre": "OMINT PLAN O5-LINEA O PRUDENTI",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "1802                ",
            "nombre": "OMINT PLAN OC-LINEA OC",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "1801                ",
            "nombre": "OMINT PLAN O-LINEA O",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "1800                ",
            "nombre": "OMINT PLAN N-LINEA N",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "1799                ",
            "nombre": "OMINT PLAN GC-LINEA GC",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "1798                ",
            "nombre": "OMINT PLAN F5-LINEA F PRUDENTI",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "1797                ",
            "nombre": "OMINT PLAN FC-LINEA FC",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "1796                ",
            "nombre": "OMINT PLAN EC-LINEA EC",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "1795                ",
            "nombre": "OMINT PLAN E-LINEA E",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "1794                ",
            "nombre": "OMINT PLAN CC-LINEA CC",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "1793                ",
            "nombre": "OMINT PLAN C-LINEA C",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "1792                ",
            "nombre": "OMINT PLAN BC-SKILL CERRADO",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "1791                ",
            "nombre": "OMINT PLAN B-LINEA SKILL",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "1790                ",
            "nombre": "OMINT PLAN A-VOLKSWAGEN",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "1788                ",
            "nombre": "DIBPFA VACUNAS",
            "codigo_obra_social": "30                  "
        },
        {
            "codigo": "1777                ",
            "nombre": "DIBPFA ACTA 100%              ",
            "codigo_obra_social": "30                  "
        },
        {
            "codigo": "1776                ",
            "nombre": "DIBPFA ACTA  70%              ",
            "codigo_obra_social": "30                  "
        },
        {
            "codigo": "1775                ",
            "nombre": "DIBPFA ACTA  40%              ",
            "codigo_obra_social": "30                  "
        },
        {
            "codigo": "1757                ",
            "nombre": "OSFATUN PREMIUM CRONICO       ",
            "codigo_obra_social": "98                  "
        },
        {
            "codigo": "1756                ",
            "nombre": "OSFATUN PREMIUM PMI           ",
            "codigo_obra_social": "98                  "
        },
        {
            "codigo": "1755                ",
            "nombre": "OSFATUN PREMIUM AMBULATORIO   ",
            "codigo_obra_social": "98                  "
        },
        {
            "codigo": "1754                ",
            "nombre": "OSFATUN INTEGRAL CRONICO      ",
            "codigo_obra_social": "98                  "
        },
        {
            "codigo": "1753                ",
            "nombre": "OSFATUN INTEGRAL PMI          ",
            "codigo_obra_social": "98                  "
        },
        {
            "codigo": "1752                ",
            "nombre": "OSFATUN INTEGRAL AMBULATORIO  ",
            "codigo_obra_social": "98                  "
        },
        {
            "codigo": "1751                ",
            "nombre": "OSFATUN BASICO O PMO CRONICO  ",
            "codigo_obra_social": "98                  "
        },
        {
            "codigo": "1750                ",
            "nombre": "OSFATUN BASICO O PMO PMI      ",
            "codigo_obra_social": "98                  "
        },
        {
            "codigo": "1749                ",
            "nombre": "OSFATUN BASICO O PMO AMBUL    ",
            "codigo_obra_social": "98                  "
        },
        {
            "codigo": "1748                ",
            "nombre": "OSPECOR PETROL MONOTRIB PMI   ",
            "codigo_obra_social": "64                  "
        },
        {
            "codigo": "1747                ",
            "nombre": "OSPECOR PETROL MONOTRIB AMBUL ",
            "codigo_obra_social": "64                  "
        },
        {
            "codigo": "1743                ",
            "nombre": "PODER JUDICIAL ESPECIAL 100%  ",
            "codigo_obra_social": "83                  "
        },
        {
            "codigo": "1742                ",
            "nombre": "PODER JUDICIAL ESPECIAL 80%   ",
            "codigo_obra_social": "83                  "
        },
        {
            "codigo": "1741                ",
            "nombre": "PODER JUDICIAL AMBUL 70%      ",
            "codigo_obra_social": "83                  "
        },
        {
            "codigo": "1729                ",
            "nombre": "VISITAR VACUNAS               ",
            "codigo_obra_social": "91                  "
        },
        {
            "codigo": "1728                ",
            "nombre": "VISITAR TIRAS REACTIVAS       ",
            "codigo_obra_social": "91                  "
        },
        {
            "codigo": "1727                ",
            "nombre": "VISITAR HIPOGLUCEMIANTES      ",
            "codigo_obra_social": "91                  "
        },
        {
            "codigo": "1726                ",
            "nombre": "VISITAR LECHES                ",
            "codigo_obra_social": "91                  "
        },
        {
            "codigo": "1725                ",
            "nombre": "VISITAR PMI                   ",
            "codigo_obra_social": "91                  "
        },
        {
            "codigo": "1724                ",
            "nombre": "VISITAR AMBULATORIO           ",
            "codigo_obra_social": "91                  "
        },
        {
            "codigo": "1723                ",
            "nombre": "OSADRA 100% PMI",
            "codigo_obra_social": "49                  "
        },
        {
            "codigo": "1722                ",
            "nombre": "OSADRA 100% INSULINAS",
            "codigo_obra_social": "49                  "
        },
        {
            "codigo": "1721                ",
            "nombre": "OSADRA  70%",
            "codigo_obra_social": "49                  "
        },
        {
            "codigo": "1720                ",
            "nombre": "OSADRA  40%",
            "codigo_obra_social": "49                  "
        },
        {
            "codigo": "1712                ",
            "nombre": "JERARQUICOS PL-PMI JUBILADOS",
            "codigo_obra_social": "42                  "
        },
        {
            "codigo": "1711                ",
            "nombre": "JERARQUICOS PL-PMI CONTINUIDAD",
            "codigo_obra_social": "42                  "
        },
        {
            "codigo": "1710                ",
            "nombre": "JERARQUICOS PL-PMI SOLTERO",
            "codigo_obra_social": "42                  "
        },
        {
            "codigo": "1709                ",
            "nombre": "JERARQUICOS PL-PMI MONOT SOLTE",
            "codigo_obra_social": "42                  "
        },
        {
            "codigo": "1708                ",
            "nombre": "JERARQUICOS PL-PMI 100%ESPECIA",
            "codigo_obra_social": "42                  "
        },
        {
            "codigo": "1707                ",
            "nombre": "JERARQUICOS PL-PMI MONOTRIBUTI",
            "codigo_obra_social": "42                  "
        },
        {
            "codigo": "1706                ",
            "nombre": "JERARQUICOS PL-PMI 2886 SOLTER",
            "codigo_obra_social": "42                  "
        },
        {
            "codigo": "1705                ",
            "nombre": "JERARQUICOS PL-PMI 70%ESPECIAL",
            "codigo_obra_social": "42                  "
        },
        {
            "codigo": "1704                ",
            "nombre": "JERARQUICOS PL-PMI2886/2000 AM",
            "codigo_obra_social": "42                  "
        },
        {
            "codigo": "1703                ",
            "nombre": "JERARQUICOS PL-PMI 2000 JUBILA",
            "codigo_obra_social": "42                  "
        },
        {
            "codigo": "1702                ",
            "nombre": "JERARQUICOS PL-PMI 2000 MONOTR",
            "codigo_obra_social": "42                  "
        },
        {
            "codigo": "1701                ",
            "nombre": "JERARQUICOS PL-PMI 3000 AMB",
            "codigo_obra_social": "42                  "
        },
        {
            "codigo": "1700                ",
            "nombre": "APROSS INSULINAS",
            "codigo_obra_social": "12                  "
        },
        {
            "codigo": "1698                ",
            "nombre": "GALENO PLATA YPF",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1697                ",
            "nombre": "GALENO PLATA 75",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1696                ",
            "nombre": "GALENO PLATA 70",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1695                ",
            "nombre": "GALENO PLATA 65",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1694                ",
            "nombre": "GALENO PLATA 60",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1693                ",
            "nombre": "GALENO PLATA 50",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1692                ",
            "nombre": "GALENO PLATA 40",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1691                ",
            "nombre": "GALENO ORO YPF",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1690                ",
            "nombre": "GALENO ORO 85",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1689                ",
            "nombre": "GALENO ORO 75",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1688                ",
            "nombre": "GALENO ORO 70",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1687                ",
            "nombre": "GALENO ORO 65",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1686                ",
            "nombre": "GALENO ORO 60",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1685                ",
            "nombre": "GALENO ORO 50",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1684                ",
            "nombre": "GALENO ORO SHELL",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1683                ",
            "nombre": "GALENO ORO 40",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1682                ",
            "nombre": "GALENO BLANCO 70",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1681                ",
            "nombre": "GALENO BLANCO 60",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1680                ",
            "nombre": "GALENO BLANCO 50",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1679                ",
            "nombre": "GALENO BLANCO 40",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1678                ",
            "nombre": "GALENO AZUL 70",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1677                ",
            "nombre": "GALENO AZUL 60",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1676                ",
            "nombre": "GALENO AZUL 50",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1675                ",
            "nombre": "GALENO AZUL 40",
            "codigo_obra_social": "35                  "
        },
        {
            "codigo": "1674                ",
            "nombre": "OSBA PMI                      ",
            "codigo_obra_social": "97                  "
        },
        {
            "codigo": "1673                ",
            "nombre": "OSBA AMBULATORIO 50%          ",
            "codigo_obra_social": "97                  "
        },
        {
            "codigo": "1672                ",
            "nombre": "OSBA AMBULATORIO 40%          ",
            "codigo_obra_social": "97                  "
        },
        {
            "codigo": "1671                ",
            "nombre": "SWISS EMB ITALIA CRONIC 70%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "1670                ",
            "nombre": "SWISS EMB ITALIA CRONIC 40%",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "1669                ",
            "nombre": "SWISS EMB ITALIA AMBULATORIO",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "1668                ",
            "nombre": "APM AMBULATORIO",
            "codigo_obra_social": "11                  "
        },
        {
            "codigo": "1653                ",
            "nombre": "OSMATA-PLAN TIRAS REACT CAFAPR",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "1652                ",
            "nombre": "OSMATA-PLAN LANCETAS CAFAPRO",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "1651                ",
            "nombre": "OSMATA-PLAN AGUJAS CAFAPRO",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "1650                ",
            "nombre": "OSMATA-PLAN INSULINAS CAFAPRO",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "1649                ",
            "nombre": "OSMATA-PLAN CRONICO RES CAFAPR",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "1648                ",
            "nombre": "OSMATA-PLAN MAT INFANT CAFAPRO",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "1647                ",
            "nombre": "OSMATA-PLAN MED INTEG CAFAPRO",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "1646                ",
            "nombre": "OSMATA-PLAN MED OBLIG CAFAPRO",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "1645                ",
            "nombre": "VALESALUD COLFACOR",
            "codigo_obra_social": "95                  "
        },
        {
            "codigo": "1644                ",
            "nombre": "COLONIA SUIZA SALUD PERSONAL",
            "codigo_obra_social": "23                  "
        },
        {
            "codigo": "1632                ",
            "nombre": "COLONIA SUIZA SALUD A TRABAJO",
            "codigo_obra_social": "23                  "
        },
        {
            "codigo": "1631                ",
            "nombre": "OSPM PMI                      ",
            "codigo_obra_social": "73                  "
        },
        {
            "codigo": "1630                ",
            "nombre": "OSPM CRONICOS                 ",
            "codigo_obra_social": "73                  "
        },
        {
            "codigo": "1629                ",
            "nombre": "OSPM AMBULATORIO              ",
            "codigo_obra_social": "73                  "
        },
        {
            "codigo": "1626                ",
            "nombre": "APROSS RESOL MINIST 398/09",
            "codigo_obra_social": "12                  "
        },
        {
            "codigo": "1623                ",
            "nombre": "OSDE-CRONICO NO AUTORIZ-GEREN ",
            "codigo_obra_social": "51                  "
        },
        {
            "codigo": "1622                ",
            "nombre": "ZURICH PMI                    ",
            "codigo_obra_social": "93                  "
        },
        {
            "codigo": "1621                ",
            "nombre": "ZURICH AMBULATORIO            ",
            "codigo_obra_social": "93                  "
        },
        {
            "codigo": "1620                ",
            "nombre": "OSPIC CRONICO                 ",
            "codigo_obra_social": "67                  "
        },
        {
            "codigo": "1619                ",
            "nombre": "OSPIC PMI                     ",
            "codigo_obra_social": "67                  "
        },
        {
            "codigo": "1618                ",
            "nombre": "OSPIC AMBULATORIO             ",
            "codigo_obra_social": "67                  "
        },
        {
            "codigo": "1617                ",
            "nombre": "OSPATCA DISCAPACIDAD-CAFAPRO- ",
            "codigo_obra_social": "61                  "
        },
        {
            "codigo": "1616                ",
            "nombre": "OSPATCA PMI-CAFAPRO-          ",
            "codigo_obra_social": "61                  "
        },
        {
            "codigo": "1615                ",
            "nombre": "OSPATCA INSULINA-CAFAPRO-     ",
            "codigo_obra_social": "61                  "
        },
        {
            "codigo": "1614                ",
            "nombre": "OSPATCA DIABETICO-CAFAPRO-    ",
            "codigo_obra_social": "61                  "
        },
        {
            "codigo": "1613                ",
            "nombre": "OSPATCA CRONICOS-CAFAPRO-     ",
            "codigo_obra_social": "61                  "
        },
        {
            "codigo": "1612                ",
            "nombre": "OSPATCA AMBULATORIO-CAFAPRO   ",
            "codigo_obra_social": "61                  "
        },
        {
            "codigo": "1611                ",
            "nombre": "SANCOR E PMI                  ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1610                ",
            "nombre": "SANCOR E AMBULATORIO          ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1609                ",
            "nombre": "SANCOR E CRONICO              ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1607                ",
            "nombre": "RECETARIO SOLIDARIO",
            "codigo_obra_social": "87                  "
        },
        {
            "codigo": "1606                ",
            "nombre": "PREMEDICAL PMI                ",
            "codigo_obra_social": "85                  "
        },
        {
            "codigo": "1605                ",
            "nombre": "PREMEDICAL AMBULATORIO        ",
            "codigo_obra_social": "85                  "
        },
        {
            "codigo": "1604                ",
            "nombre": "SANCOR C PMI                  ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1603                ",
            "nombre": "SANCOR C CRONICO              ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1602                ",
            "nombre": "SANCOR S500 PMI               ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1601                ",
            "nombre": "SANCOR S500 CRONICO           ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1600                ",
            "nombre": "SANCOR S4000 PMI              ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1599                ",
            "nombre": "SANCOR S4000 CRONICO          ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1598                ",
            "nombre": "SANCOR S3000 CRONICO          ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1597                ",
            "nombre": "SANCOR S3000 PMI              ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1596                ",
            "nombre": "SANCOR S2000 PMI              ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1595                ",
            "nombre": "SANCOR S2000 CRONICO          ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1594                ",
            "nombre": "SANCOR S1000 PMI              ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1593                ",
            "nombre": "SANCOR S1000 CRONICO          ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1592                ",
            "nombre": "SANCOR C AMBULATORIO          ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1591                ",
            "nombre": "SANCOR S4000 AMBULATORIO      ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1590                ",
            "nombre": "SANCOR S3000 AMBULATORIO      ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1589                ",
            "nombre": "SANCOR S2000 AMBULATORIO      ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1588                ",
            "nombre": "SANCOR S1000 AMBULATORIO      ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1587                ",
            "nombre": "SANCOR S500 AMBULATORIO       ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1586                ",
            "nombre": "ARISTON PLAN PMI              ",
            "codigo_obra_social": "14                  "
        },
        {
            "codigo": "1585                ",
            "nombre": "ARISTON PLAN SALUD AMBUL      ",
            "codigo_obra_social": "14                  "
        },
        {
            "codigo": "1584                ",
            "nombre": "ARISTON PLAN FAMILIA AMBUL    ",
            "codigo_obra_social": "14                  "
        },
        {
            "codigo": "1583                ",
            "nombre": "ARISTON PLAN JOVEN AMBUL      ",
            "codigo_obra_social": "14                  "
        },
        {
            "codigo": "1582                ",
            "nombre": "ARISTON PLAN PLATA AMBUL      ",
            "codigo_obra_social": "14                  "
        },
        {
            "codigo": "1581                ",
            "nombre": "ARISTON PLAN ORO PLUS AMBUL   ",
            "codigo_obra_social": "14                  "
        },
        {
            "codigo": "1580                ",
            "nombre": "ARISTON PLAN ORO AMBUL        ",
            "codigo_obra_social": "14                  "
        },
        {
            "codigo": "1579                ",
            "nombre": "SANCOR AMJUB AMBULATORIO      ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1578                ",
            "nombre": "SANCOR AMADH PMI              ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1577                ",
            "nombre": "SANCOR AMADH CRONICOS         ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1576                ",
            "nombre": "SANCOR AMADH AMBULATORIO      ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1566                ",
            "nombre": "OSSEG SEG PLAN INTEGRAL PLUS  ",
            "codigo_obra_social": "75                  "
        },
        {
            "codigo": "1565                ",
            "nombre": "SANCOR SEGUROS P-BCO CBA OTC  ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1564                ",
            "nombre": "SANCOR SEGUROS P-BCO CBA AMBU ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1563                ",
            "nombre": "OSSEG SEG PLAN INTEGRAL ADHERE",
            "codigo_obra_social": "75                  "
        },
        {
            "codigo": "1562                ",
            "nombre": "PAMI COSEGUROS",
            "codigo_obra_social": "80                  "
        },
        {
            "codigo": "1561                ",
            "nombre": "APROSS RES 40/5 COSEG",
            "codigo_obra_social": "12                  "
        },
        {
            "codigo": "1560                ",
            "nombre": "APROSS RES 40/5 AMBULAT",
            "codigo_obra_social": "12                  "
        },
        {
            "codigo": "1559                ",
            "nombre": "OSCTCP UTA PMI",
            "codigo_obra_social": "99                  "
        },
        {
            "codigo": "1558                ",
            "nombre": "OSCTCP UTA AMBULAT 100%",
            "codigo_obra_social": "99                  "
        },
        {
            "codigo": "1557                ",
            "nombre": "OSCTCP UTA AMBULAT 70%",
            "codigo_obra_social": "99                  "
        },
        {
            "codigo": "1556                ",
            "nombre": "OSCTCP UTA AMBULAT 40%",
            "codigo_obra_social": "99                  "
        },
        {
            "codigo": "1555                ",
            "nombre": "AMTTAC LECHE                  ",
            "codigo_obra_social": "9                   "
        },
        {
            "codigo": "1554                ",
            "nombre": "AMTTAC MS-405                 ",
            "codigo_obra_social": "9                   "
        },
        {
            "codigo": "1553                ",
            "nombre": "AMTTAC MS-505                 ",
            "codigo_obra_social": "9                   "
        },
        {
            "codigo": "1552                ",
            "nombre": "AMTTAC MS-205                 ",
            "codigo_obra_social": "9                   "
        },
        {
            "codigo": "1551                ",
            "nombre": "OSIM ANTICONCEPTIVOS          ",
            "codigo_obra_social": "55                  "
        },
        {
            "codigo": "1550                ",
            "nombre": "OSIM INSUMOS DIABETES         ",
            "codigo_obra_social": "55                  "
        },
        {
            "codigo": "1549                ",
            "nombre": "OSIM DISCAPACIDAD             ",
            "codigo_obra_social": "55                  "
        },
        {
            "codigo": "1548                ",
            "nombre": "OSIM HIPOGLUCEMIANTES         ",
            "codigo_obra_social": "55                  "
        },
        {
            "codigo": "1547                ",
            "nombre": "OSIM RES 310 CRONICO          ",
            "codigo_obra_social": "55                  "
        },
        {
            "codigo": "1546                ",
            "nombre": "OSIM PLAN MATERNO             ",
            "codigo_obra_social": "55                  "
        },
        {
            "codigo": "1545                ",
            "nombre": "SANCOR A500 PMI               ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1544                ",
            "nombre": "SANCOR A500 CRONICO           ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1543                ",
            "nombre": "SANCOR A500 AMBULATORIO       ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1542                ",
            "nombre": "SANCOR OS CRONICO             ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1541                ",
            "nombre": "SANCOR AMCC CRONICO           ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1540                ",
            "nombre": "SANCOR A4000 CRONICO          ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1539                ",
            "nombre": "SANCOR A3000 CRONICO          ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1538                ",
            "nombre": "SANCOR A2000 CRONICO          ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1537                ",
            "nombre": "SANCOR A1000 CRONICO          ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1536                ",
            "nombre": "SANCOR OS PMI                 ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1535                ",
            "nombre": "SANCOR AMCC PMI               ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1534                ",
            "nombre": "SANCOR A4000 PMI              ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1533                ",
            "nombre": "SANCOR A3000 PMI              ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1532                ",
            "nombre": "SANCOR A2000 PMI              ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1531                ",
            "nombre": "SANCOR A1000 PMI              ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1530                ",
            "nombre": "SANCOR OS AMBULATORIO         ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1529                ",
            "nombre": "SANCOR AMCC AMBULATORIO       ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1527                ",
            "nombre": "SANCOR A1000 AMBULATORIO      ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1526                ",
            "nombre": "SANCOR A2000 AMBULATORIO      ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1525                ",
            "nombre": "SANCOR A3000 AMBULATORIO      ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1524                ",
            "nombre": "SANCOR A4000 AMBULATORIO      ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1521                ",
            "nombre": "OSTV PMI                      ",
            "codigo_obra_social": "78                  "
        },
        {
            "codigo": "1520                ",
            "nombre": "OSTV PLAN PLUS/ULTRA 70%      ",
            "codigo_obra_social": "78                  "
        },
        {
            "codigo": "1519                ",
            "nombre": "OSTV PLAN PLUS/ULTRA AMBUL    ",
            "codigo_obra_social": "78                  "
        },
        {
            "codigo": "1518                ",
            "nombre": "OSTV PLAN CLASSIC 70%         ",
            "codigo_obra_social": "78                  "
        },
        {
            "codigo": "1516                ",
            "nombre": "OSTV PLAN CLASSIC AMBULAT     ",
            "codigo_obra_social": "78                  "
        },
        {
            "codigo": "1433                ",
            "nombre": "CRS-OSPM DELTA X AMB          ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1432                ",
            "nombre": "CRS-OSPM GAMMA X AMB          ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1431                ",
            "nombre": "CRS-OSPM BETA X AMB           ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1430                ",
            "nombre": "CRS-OSPM ALFA X AMB           ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1429                ",
            "nombre": "CRS-OSPOCE DELTA X AMB        ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1427                ",
            "nombre": "CRS-OSPOCE BETA X AMB         ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1426                ",
            "nombre": "CRS-OSPOCE ALFA X AMB         ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1425                ",
            "nombre": "CRS-OSCEP DELTA X AMB         ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1424                ",
            "nombre": "CRS-OSCEP GAMMA X AMB         ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1423                ",
            "nombre": "CRS-OSCEP ALFA X AMB          ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1422                ",
            "nombre": "CRS-DELTA X AMB               ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1421                ",
            "nombre": "CRS-BETA X AMBU               ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1420                ",
            "nombre": "CRS-ALFA X AMB                ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1419                ",
            "nombre": "CRS ASE-300 X AMB             ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1418                ",
            "nombre": "CRS ASE-200 X AMB             ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1417                ",
            "nombre": "CRS ASE-100 X AMB             ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1415                ",
            "nombre": "CRS-OSPM GAMMA PMI            ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1414                ",
            "nombre": "CRS-OSPM GAMMA AMB            ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1413                ",
            "nombre": "CRS-OSPM BETA PMI             ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1412                ",
            "nombre": "CRS-OSPM BETA AMB             ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1411                ",
            "nombre": "CRS-OSPM ALFA PMI             ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1410                ",
            "nombre": "CRS-OSPM ALFA AMB             ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1409                ",
            "nombre": "CRS-OSPM PMO PMI              ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1408                ",
            "nombre": "CRS-OSPM PMO AMB              ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1407                ",
            "nombre": "CRS-OSCEP GAMMA PMI           ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1406                ",
            "nombre": "CRS-OSCEP GAMMA AMB           ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1405                ",
            "nombre": "CRS-OSPOCE BETA PMI           ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1404                ",
            "nombre": "CRS-OSPOCE BETA AMB           ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1403                ",
            "nombre": "CRS-OSPOCE ALFA PMI           ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1402                ",
            "nombre": "CRS-OSPOCE ALFA AMB           ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1401                ",
            "nombre": "CRS-OSCEP BETA X AMB          ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1400                ",
            "nombre": "CRS-OSCEP BETA PMI            ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1399                ",
            "nombre": "CRS-OSCEP BETA AMB            ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1398                ",
            "nombre": "CRS-OSCEP ALFA PMI            ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1397                ",
            "nombre": "CRS-OSCEP ALFA AMB            ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1396                ",
            "nombre": "CRS-OSCEP PMO PMI             ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1395                ",
            "nombre": "CRS-OSCEP PMO AMB             ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1394                ",
            "nombre": "ANDAR AUTORIZACION ESPECIAL   ",
            "codigo_obra_social": "10                  "
        },
        {
            "codigo": "1393                ",
            "nombre": "UNIMED OSSDEB INTEGRAL CRONICO",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1392                ",
            "nombre": "UNIMED OSSDEB INTEGRAL 100%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1391                ",
            "nombre": "UNIMED OSSDEB INTEGRAL AMB",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1388                ",
            "nombre": "AMPIL PLAN SUPERADOR",
            "codigo_obra_social": "95                  "
        },
        {
            "codigo": "1367                ",
            "nombre": "ANDAR PROG PROCREACION RESP   ",
            "codigo_obra_social": "10                  "
        },
        {
            "codigo": "1366                ",
            "nombre": "ANDAR PSICOFARMACOS           ",
            "codigo_obra_social": "10                  "
        },
        {
            "codigo": "1365                ",
            "nombre": "ANDAR CRONICO M FIJO          ",
            "codigo_obra_social": "10                  "
        },
        {
            "codigo": "1352                ",
            "nombre": "UNIMED OSFOT PMI",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1351                ",
            "nombre": "UNIMED OSFOT AMB",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1348                ",
            "nombre": "NOBIS PLATINO                 ",
            "codigo_obra_social": "47                  "
        },
        {
            "codigo": "1347                ",
            "nombre": "NOBIS AMBAR                   ",
            "codigo_obra_social": "47                  "
        },
        {
            "codigo": "1346                ",
            "nombre": "NOBIS RUBI                    ",
            "codigo_obra_social": "47                  "
        },
        {
            "codigo": "1344                ",
            "nombre": "NOBIS DIAMANTE                ",
            "codigo_obra_social": "47                  "
        },
        {
            "codigo": "1341                ",
            "nombre": "OSPF AMBULATORIO 70%          ",
            "codigo_obra_social": "66                  "
        },
        {
            "codigo": "1339                ",
            "nombre": "OSPIL PLAN SUPERADOR",
            "codigo_obra_social": "68                  "
        },
        {
            "codigo": "1338                ",
            "nombre": "OSPF DESCARTABLE              ",
            "codigo_obra_social": "66                  "
        },
        {
            "codigo": "1337                ",
            "nombre": "OSPF ESPECIAL AL 100%         ",
            "codigo_obra_social": "66                  "
        },
        {
            "codigo": "1336                ",
            "nombre": "OSPF PMI                      ",
            "codigo_obra_social": "66                  "
        },
        {
            "codigo": "1335                ",
            "nombre": "OSPF CONVENIO COLECTIVO       ",
            "codigo_obra_social": "66                  "
        },
        {
            "codigo": "1334                ",
            "nombre": "OSPF AMBULATORIO 40%          ",
            "codigo_obra_social": "66                  "
        },
        {
            "codigo": "1333                ",
            "nombre": "UNIMED TOTAL  CRONICOS",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1332                ",
            "nombre": "UNIMED SIA SALUD CRONICO",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1331                ",
            "nombre": "UNIMED PROSALUD CRONICOS",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1330                ",
            "nombre": "UNIMED OSTV HORUS CRONICO",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1329                ",
            "nombre": "UNIMED OSSDEB HORUS CRONICOS",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1328                ",
            "nombre": "UNIMED OSPOCE PLAN ROBLE CRONI",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1327                ",
            "nombre": "UNIMED OSPOCE PLAN CEIBO CRONI",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1326                ",
            "nombre": "UNIMED OSPOCE PLAN ARRAYAN CRO",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1325                ",
            "nombre": "UNIMED OSPOCE INTEG APEX CRONI",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1324                ",
            "nombre": "UNIMED OSPATRONES SUP CRONICOS",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1319                ",
            "nombre": "AMP PLAN-DIAMANTE JOVEN INTERN",
            "codigo_obra_social": "8                   "
        },
        {
            "codigo": "1318                ",
            "nombre": "AMP PLAN RUBI INTERNACION     ",
            "codigo_obra_social": "8                   "
        },
        {
            "codigo": "1317                ",
            "nombre": "AMP PLAN DIAMANTE INTERNACION ",
            "codigo_obra_social": "8                   "
        },
        {
            "codigo": "1316                ",
            "nombre": "AMP PLAN AMBAR INTERNACION    ",
            "codigo_obra_social": "8                   "
        },
        {
            "codigo": "1315                ",
            "nombre": "COLFACOR VALE                 ",
            "codigo_obra_social": "22                  "
        },
        {
            "codigo": "1312                ",
            "nombre": "OSDE DIRECTO ESPECIAL 100%    ",
            "codigo_obra_social": "51                  "
        },
        {
            "codigo": "1311                ",
            "nombre": "OSDE DIRECTO CRONICOS         ",
            "codigo_obra_social": "51                  "
        },
        {
            "codigo": "1310                ",
            "nombre": "OSDE DIRECTO AMBULATORIO      ",
            "codigo_obra_social": "51                  "
        },
        {
            "codigo": "1309                ",
            "nombre": "CRS-ALFA PMI                  ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1308                ",
            "nombre": "CRS-ALFA AMB                  ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1307                ",
            "nombre": "UNIMED TOTAL AMBULATORIO",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1306                ",
            "nombre": "UNIMED HORUS 65  100%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1305                ",
            "nombre": "UNIMED LOOCKEED MARTIN 100%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1304                ",
            "nombre": "UNIMED HORUS 65 AMBULATORIO",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1303                ",
            "nombre": "OSITAC-AOITA PMI S/AUTORIZ    ",
            "codigo_obra_social": "56                  "
        },
        {
            "codigo": "1302                ",
            "nombre": "OSITAC-AOITA CRONIC S/AUTORIZ ",
            "codigo_obra_social": "56                  "
        },
        {
            "codigo": "1301                ",
            "nombre": "OSITAC-AOITA CRONICOS         ",
            "codigo_obra_social": "56                  "
        },
        {
            "codigo": "1300                ",
            "nombre": "COLFACOR VALE S/RECETA        ",
            "codigo_obra_social": "22                  "
        },
        {
            "codigo": "1299M               ",
            "nombre": "PAMI RESOLUCION 337 MANUAL",
            "codigo_obra_social": "PAMIMANUAL          "
        },
        {
            "codigo": "1299                ",
            "nombre": "PAMI RESOLUCION 337",
            "codigo_obra_social": "80                  "
        },
        {
            "codigo": "1299                ",
            "nombre": "PAMI RES-337 COSEGUROS",
            "codigo_obra_social": "80                  "
        },
        {
            "codigo": "1296                ",
            "nombre": "UNIMED OSPATRONES INTEGRAL CRO",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1295                ",
            "nombre": "UNIMED OSPATRONES ESPEC CRONIC",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1294                ",
            "nombre": "UNIMED OSCEP HORUS CRONICO",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1293                ",
            "nombre": "UNIMED LOOCKEED MARTIN CRONICO",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1292                ",
            "nombre": "UNIMED ASSPE HORUS CRONICO",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1291                ",
            "nombre": "UNIMED AFIP I CRONICO",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1283                ",
            "nombre": "AMP PLAN-DIAMANTE JOVEN PMI   ",
            "codigo_obra_social": "8                   "
        },
        {
            "codigo": "1282                ",
            "nombre": "AMP PLAN-DIAMANTE JOVEN AMBULA",
            "codigo_obra_social": "8                   "
        },
        {
            "codigo": "1280                ",
            "nombre": "AMP PLAN DIAMANTE PMI         ",
            "codigo_obra_social": "8                   "
        },
        {
            "codigo": "1279                ",
            "nombre": "AMP PLAN DIAMANTE AMBULATORIO ",
            "codigo_obra_social": "8                   "
        },
        {
            "codigo": "1277                ",
            "nombre": "AMP PLAN RUBI PMI             ",
            "codigo_obra_social": "8                   "
        },
        {
            "codigo": "1275                ",
            "nombre": "AMP PLAN AMBAR PMI            ",
            "codigo_obra_social": "8                   "
        },
        {
            "codigo": "1274                ",
            "nombre": "AMP PLAN RUBI AMBULATORIO     ",
            "codigo_obra_social": "8                   "
        },
        {
            "codigo": "1273                ",
            "nombre": "AMP PLAN AMBAR AMBULATORIO    ",
            "codigo_obra_social": "8                   "
        },
        {
            "codigo": "1250                ",
            "nombre": "OSPEP PMI (GESALCOR)          ",
            "codigo_obra_social": "65                  "
        },
        {
            "codigo": "1249                ",
            "nombre": "OSPEP AMBULATORIO(GESALCOR)   ",
            "codigo_obra_social": "65                  "
        },
        {
            "codigo": "1245                ",
            "nombre": "ANDAR MONOTRIB PMI            ",
            "codigo_obra_social": "10                  "
        },
        {
            "codigo": "1244                ",
            "nombre": "ACA SALUD PLAN 52             ",
            "codigo_obra_social": "3                   "
        },
        {
            "codigo": "1243                ",
            "nombre": "ACA SALUD PLAN 51             ",
            "codigo_obra_social": "3                   "
        },
        {
            "codigo": "1242                ",
            "nombre": "ACA SALUD PLAN 50             ",
            "codigo_obra_social": "3                   "
        },
        {
            "codigo": "1241                ",
            "nombre": "ACA SALUD PLAN CERCA          ",
            "codigo_obra_social": "3                   "
        },
        {
            "codigo": "1240                ",
            "nombre": "ACA SALUD PLAN 9              ",
            "codigo_obra_social": "3                   "
        },
        {
            "codigo": "1236                ",
            "nombre": "ACA SALUD PLAN 1 A. CORPORAT  ",
            "codigo_obra_social": "3                   "
        },
        {
            "codigo": "1235                ",
            "nombre": "ACA SALUD PLAN 18             ",
            "codigo_obra_social": "3                   "
        },
        {
            "codigo": "1234                ",
            "nombre": "ACA SALUD PLAN 11             ",
            "codigo_obra_social": "3                   "
        },
        {
            "codigo": "1233                ",
            "nombre": "ACA SALUD PLAN 4              ",
            "codigo_obra_social": "3                   "
        },
        {
            "codigo": "1232                ",
            "nombre": "ACA SALUD PLAN 1              ",
            "codigo_obra_social": "3                   "
        },
        {
            "codigo": "1231                ",
            "nombre": "ACA SALUD PLAN 23 A CORPORAT  ",
            "codigo_obra_social": "3                   "
        },
        {
            "codigo": "1228                ",
            "nombre": "SWISS APSOT Y FSST PMI",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "1227                ",
            "nombre": "SWISS PMO INFANTIL",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "1226                ",
            "nombre": "SWISS PMO DIABET HIPOGLUCEM",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "1225                ",
            "nombre": "SWISS APSOT BASICO AMBULAT",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "1224                ",
            "nombre": "SWISS APSOT Y FSST AMBULAT",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "1223                ",
            "nombre": "SWISS DOCTHOS AMBULAT",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "1222                ",
            "nombre": "SWISS NUBIAL AMBULAT",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "1221                ",
            "nombre": "SWISS MEDICIEN AMBULAT",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "1220                ",
            "nombre": "SWISS OPTAR AMBULAT",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "1219                ",
            "nombre": "SWISS QUALITAS AMBULAT",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "1199                ",
            "nombre": "ACONCAGUA SALUD PMI           ",
            "codigo_obra_social": "4                   "
        },
        {
            "codigo": "1198                ",
            "nombre": "ACONCAGUA SALUD AMBULATORIO   ",
            "codigo_obra_social": "4                   "
        },
        {
            "codigo": "1197                ",
            "nombre": "UNIMED SIA SALUD TOTAL AMB",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1196                ",
            "nombre": "UNIMED SIA SALUD MAGNO AMB",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1195                ",
            "nombre": "UNIMED OSTV HORUS 85 AMBUL",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1194                ",
            "nombre": "UNIMED OSCEP HORUS 85 AMB",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1193                ",
            "nombre": "UNIMED OSPOCE HORUS 85 AMB",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1192                ",
            "nombre": "UNIMED OSPOCE HORUS CRONICOS",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1191                ",
            "nombre": "UNIMED PROSALUD 95 AMBULATORIO",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1190                ",
            "nombre": "UNIMED OSSDEB HORUS 85 AMB",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1189                ",
            "nombre": "GEO SALUD 50% AUTORIZADAS     ",
            "codigo_obra_social": "37                  "
        },
        {
            "codigo": "1188                ",
            "nombre": "GEO SALUD AUTORIZADAS         ",
            "codigo_obra_social": "37                  "
        },
        {
            "codigo": "1186                ",
            "nombre": "GEO SALUD PMI                 ",
            "codigo_obra_social": "37                  "
        },
        {
            "codigo": "1185                ",
            "nombre": "GEO SALUD AMBULATORIO         ",
            "codigo_obra_social": "37                  "
        },
        {
            "codigo": "1147                ",
            "nombre": "PAMI POR RAZONES SOCIALES",
            "codigo_obra_social": "80                  "
        },
        {
            "codigo": "1146                ",
            "nombre": "PAMI POR VIA DE EXCEPCION",
            "codigo_obra_social": "80                  "
        },
        {
            "codigo": "1141                ",
            "nombre": "CRS-OSPOCE GAMMA PMI          ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1140                ",
            "nombre": "CRS-OSPOCE GAMMA AMB          ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1139                ",
            "nombre": "CRS-GAMMA PMI                 ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1138                ",
            "nombre": "CRS-GAMMA AMB                 ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1137                ",
            "nombre": "CRS-BETA PMI                  ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1136                ",
            "nombre": "CRS-BETA AMBU                 ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1134                ",
            "nombre": "OSTIG PMI-GESALCOR            ",
            "codigo_obra_social": "77                  "
        },
        {
            "codigo": "1133                ",
            "nombre": "OSTIG AMBUL-GESALCOR          ",
            "codigo_obra_social": "77                  "
        },
        {
            "codigo": "1123                ",
            "nombre": "UNIMED OSPATRONES INTEGRAL 100",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1122                ",
            "nombre": "UNIMED OSPATRONES ESPECIAL 100",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1121                ",
            "nombre": "UNIMED OSPATRONES SUPERIOR 100",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1120                ",
            "nombre": "UNIMED OSPATRONES INTEGRAL",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1119                ",
            "nombre": "UNIMED OSPATRONES ESPECIAL",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1118                ",
            "nombre": "UNIMED OSPATRONES SUPERIOR",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1117                ",
            "nombre": "ANDAR PLAN PLUS PMI           ",
            "codigo_obra_social": "10                  "
        },
        {
            "codigo": "1116                ",
            "nombre": "ANDAR PLAN ESPECIAL PMI       ",
            "codigo_obra_social": "10                  "
        },
        {
            "codigo": "1115                ",
            "nombre": "ANDAR PLAN CLASICO PMI        ",
            "codigo_obra_social": "10                  "
        },
        {
            "codigo": "1114                ",
            "nombre": "OSITAC-AOITA PMI              ",
            "codigo_obra_social": "56                  "
        },
        {
            "codigo": "1113                ",
            "nombre": "OSPECOR GESALCOR PMI          ",
            "codigo_obra_social": "64                  "
        },
        {
            "codigo": "1112                ",
            "nombre": "OSPECOR GESALCOR AMBULAT      ",
            "codigo_obra_social": "64                  "
        },
        {
            "codigo": "1107                ",
            "nombre": "OSSEG ESPECIAL RESOL 310      ",
            "codigo_obra_social": "75                  "
        },
        {
            "codigo": "1105                ",
            "nombre": "FIAT CRONICOS MEPC            ",
            "codigo_obra_social": "34                  "
        },
        {
            "codigo": "1104                ",
            "nombre": "FIAT INSULINAS                ",
            "codigo_obra_social": "34                  "
        },
        {
            "codigo": "1102                ",
            "nombre": "CRS-OSCEP 45 PMI              ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1101                ",
            "nombre": "CRS-OSCEP 45 AMB              ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1099                ",
            "nombre": "CRS-ROMAGOSA DIRECTO AMB      ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1098                ",
            "nombre": "CRS ASE-300 AMB               ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1097                ",
            "nombre": "CRS ASE-100 AMB               ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1096                ",
            "nombre": "CRS ASE-200 PMI               ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1095                ",
            "nombre": "CRS ASE-200 AMB               ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1094                ",
            "nombre": "CRS ASE-100 PMI               ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1093                ",
            "nombre": "CRS ASE-300 PMI               ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1092                ",
            "nombre": "OSPIL CRONICOS",
            "codigo_obra_social": "68                  "
        },
        {
            "codigo": "1091                ",
            "nombre": "OSPA CRONICOS                 ",
            "codigo_obra_social": "59                  "
        },
        {
            "codigo": "1090                ",
            "nombre": "SANCOR SEGUROS AMBULATORIO    ",
            "codigo_obra_social": "89                  "
        },
        {
            "codigo": "1089                ",
            "nombre": "OSMATA CRONICOS",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "1085                ",
            "nombre": "APROSS ONCOLOGICO",
            "codigo_obra_social": "12                  "
        },
        {
            "codigo": "1084                ",
            "nombre": "APROSS TRAT ESPECIALES",
            "codigo_obra_social": "12                  "
        },
        {
            "codigo": "1083                ",
            "nombre": "UNIMED OSTV HORUS 100%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1082                ",
            "nombre": "UNIMED OSTV HORUS AMBUL",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1072                ",
            "nombre": "PARQUE SALUD PMI              ",
            "codigo_obra_social": "81                  "
        },
        {
            "codigo": "1071                ",
            "nombre": "PARQUE SALUD AMBULATORIO      ",
            "codigo_obra_social": "81                  "
        },
        {
            "codigo": "1070                ",
            "nombre": "COVER SALUD PMI               ",
            "codigo_obra_social": "25                  "
        },
        {
            "codigo": "1069                ",
            "nombre": "FEDERADA 200 Y 200E",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "1068                ",
            "nombre": "COVER SALUD PLAN 804          ",
            "codigo_obra_social": "25                  "
        },
        {
            "codigo": "1067                ",
            "nombre": "COVER SALUD PLAN 801 y 803    ",
            "codigo_obra_social": "25                  "
        },
        {
            "codigo": "1064                ",
            "nombre": "VOLKSWAGEN VACUNAS            ",
            "codigo_obra_social": "92                  "
        },
        {
            "codigo": "1063                ",
            "nombre": "VOLKSWAGEN S/RES 310 Y 758    ",
            "codigo_obra_social": "92                  "
        },
        {
            "codigo": "1062                ",
            "nombre": "VOLKSWAGEN S/RES 310 Y 758    ",
            "codigo_obra_social": "92                  "
        },
        {
            "codigo": "1061                ",
            "nombre": "VOLKSWAGEN PMI                ",
            "codigo_obra_social": "92                  "
        },
        {
            "codigo": "1060                ",
            "nombre": "VOLKSWAGEN AMBULATORIO        ",
            "codigo_obra_social": "92                  "
        },
        {
            "codigo": "1059                ",
            "nombre": "UNIMED ASSPE HORUS 100%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1058                ",
            "nombre": "UNIMED ASSPE HORUS AMB",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1055                ",
            "nombre": "UNIMED OSPOCE INTEG APEX PMI",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1054                ",
            "nombre": "UNIMED OSPOCE INTEG APEX",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1052                ",
            "nombre": "OSTIG ANTICONCEP-ANTITUBERCULO",
            "codigo_obra_social": "77                  "
        },
        {
            "codigo": "1048                ",
            "nombre": "UNIMED TOTAL  100%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1047                ",
            "nombre": "UNIMED LOOCKEED MARTIN AMB",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1046                ",
            "nombre": "UNIMED AFIP I 100%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1045                ",
            "nombre": "UNIMED AFIP I AMB",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1042                ",
            "nombre": "CRS-MAYOR PAMI                ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1041                ",
            "nombre": "CRS-MAYOR AMB                 ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1040                ",
            "nombre": "CRS-ROMAGOSA DIRECTO PMI      ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "1036                ",
            "nombre": "OSECAC MONOTRIB AUTORIZ 70%   ",
            "codigo_obra_social": "54                  "
        },
        {
            "codigo": "1035                ",
            "nombre": "OSECAC 70%                    ",
            "codigo_obra_social": "54                  "
        },
        {
            "codigo": "1034                ",
            "nombre": "OSECAC MONOTRIB PPI           ",
            "codigo_obra_social": "54                  "
        },
        {
            "codigo": "1033                ",
            "nombre": "OSECAC MONOTRIB PMI           ",
            "codigo_obra_social": "54                  "
        },
        {
            "codigo": "1032                ",
            "nombre": "OSECAC MONOTRIBUTO",
            "codigo_obra_social": "54                  "
        },
        {
            "codigo": "1031                ",
            "nombre": "UNIMED SIA SALUD 100%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1030                ",
            "nombre": "UNIMED SIA SALUD JOVEN AMB",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1029                ",
            "nombre": "UNIMED OSCEP  HORUS 100%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1028                ",
            "nombre": "UNIMED OSCEP  HORUS AMB",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1027                ",
            "nombre": "UNIMED OSSDEB HORUS 100%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1026                ",
            "nombre": "UNIMED OSSDEB HORUS AMB",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1025                ",
            "nombre": "UNIMED OSPOCE HORUS 100%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1024                ",
            "nombre": "UNIMED OSPOCE HORUS AMB",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1023                ",
            "nombre": "UNIMED PROSALUD 100%",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1022                ",
            "nombre": "UNIMED PROSALUD AMBULATORIO",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "1020                ",
            "nombre": "APROSS CRONICOS",
            "codigo_obra_social": "12                  "
        },
        {
            "codigo": "1018                ",
            "nombre": "OSECAC PPI                    ",
            "codigo_obra_social": "54                  "
        },
        {
            "codigo": "1016                ",
            "nombre": "CEMEC PLAN B-AMBULATORIO      ",
            "codigo_obra_social": "19                  "
        },
        {
            "codigo": "1015                ",
            "nombre": "CEMEC PLAN A -AMBULATORIO     ",
            "codigo_obra_social": "19                  "
        },
        {
            "codigo": "1008                ",
            "nombre": "AMFECOF ESTUDIANTIL AMBULATORI",
            "codigo_obra_social": "7                   "
        },
        {
            "codigo": "1007                ",
            "nombre": "AMFECOF SOLIDARIO AMBULATORIO ",
            "codigo_obra_social": "7                   "
        },
        {
            "codigo": "1006                ",
            "nombre": "AMFECOF MUTUAL AMBULATORIO    ",
            "codigo_obra_social": "7                   "
        },
        {
            "codigo": "1005                ",
            "nombre": "AMFECOF FAMILIA PMI           ",
            "codigo_obra_social": "7                   "
        },
        {
            "codigo": "1004                ",
            "nombre": "AMFECOF FAMILIA AMBULATORIO   ",
            "codigo_obra_social": "7                   "
        },
        {
            "codigo": "1003                ",
            "nombre": "AMFECOF CLUB PMI              ",
            "codigo_obra_social": "7                   "
        },
        {
            "codigo": "1002                ",
            "nombre": "AMFECOF CLUB AMBULATORIO      ",
            "codigo_obra_social": "7                   "
        },
        {
            "codigo": "1001                ",
            "nombre": "AMFECOF PREMIUM PMI           ",
            "codigo_obra_social": "7                   "
        },
        {
            "codigo": "1000                ",
            "nombre": "AMFECOF PREMIUM AMBULATORIO   ",
            "codigo_obra_social": "7                   "
        },
        {
            "codigo": "999                 ",
            "nombre": "AMFECOF PLATEADO PMI          ",
            "codigo_obra_social": "7                   "
        },
        {
            "codigo": "998                 ",
            "nombre": "AMFECOF PLATEADO AMBULATORIO  ",
            "codigo_obra_social": "7                   "
        },
        {
            "codigo": "997                 ",
            "nombre": "AMFECOF DORADO PMI            ",
            "codigo_obra_social": "7                   "
        },
        {
            "codigo": "996                 ",
            "nombre": "AMFECOF DORADO AMBULATORIO    ",
            "codigo_obra_social": "7                   "
        },
        {
            "codigo": "980                 ",
            "nombre": "OSIM AMBULATORIO              ",
            "codigo_obra_social": "55                  "
        },
        {
            "codigo": "978                 ",
            "nombre": "OSMATA JER. LANC. Y AGUJAS",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "976                 ",
            "nombre": "FEDERADA PLAN 10 Y 10E",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "972                 ",
            "nombre": "OSPACA PMI 03-04-05-06",
            "codigo_obra_social": "60                  "
        },
        {
            "codigo": "971                 ",
            "nombre": "OSPACA AMBU 07",
            "codigo_obra_social": "60                  "
        },
        {
            "codigo": "970                 ",
            "nombre": "OSPACA PMI 07",
            "codigo_obra_social": "60                  "
        },
        {
            "codigo": "969                 ",
            "nombre": "OSPACA AMBU 06",
            "codigo_obra_social": "60                  "
        },
        {
            "codigo": "968                 ",
            "nombre": "OSPACA AMBU 05",
            "codigo_obra_social": "60                  "
        },
        {
            "codigo": "954                 ",
            "nombre": "MEDIFE PLAN FIAT 75%          ",
            "codigo_obra_social": "45                  "
        },
        {
            "codigo": "953                 ",
            "nombre": "MEDIFE PLAN FIAT 40%          ",
            "codigo_obra_social": "45                  "
        },
        {
            "codigo": "952                 ",
            "nombre": "MEDIFE CREDENCIAL 50%         ",
            "codigo_obra_social": "45                  "
        },
        {
            "codigo": "950                 ",
            "nombre": "OSTIG DIABETES                ",
            "codigo_obra_social": "77                  "
        },
        {
            "codigo": "949                 ",
            "nombre": "OSTIG INSULINAS               ",
            "codigo_obra_social": "77                  "
        },
        {
            "codigo": "948                 ",
            "nombre": "OSPA CUPON VERDE              ",
            "codigo_obra_social": "59                  "
        },
        {
            "codigo": "947                 ",
            "nombre": "OSPA PMI Y OTRAS AUTORIZACIONE",
            "codigo_obra_social": "59                  "
        },
        {
            "codigo": "945                 ",
            "nombre": "OSPA TIRAS REACTIVAS          ",
            "codigo_obra_social": "59                  "
        },
        {
            "codigo": "942                 ",
            "nombre": "OSPA CUPON ROJO               ",
            "codigo_obra_social": "59                  "
        },
        {
            "codigo": "941                 ",
            "nombre": "VALESALUD",
            "codigo_obra_social": "95                  "
        },
        {
            "codigo": "938                 ",
            "nombre": "MET PMI",
            "codigo_obra_social": "46                  "
        },
        {
            "codigo": "937                 ",
            "nombre": "MET MT P1",
            "codigo_obra_social": "46                  "
        },
        {
            "codigo": "936                 ",
            "nombre": "MET MTB C",
            "codigo_obra_social": "46                  "
        },
        {
            "codigo": "931                 ",
            "nombre": "FEDERADA SALUD INTERNACION",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "930                 ",
            "nombre": "FEDERADA SALUD PMI",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "929                 ",
            "nombre": "FEDERADA SALUD AMBULATORIO",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "928                 ",
            "nombre": "PODER JUDICIAL ESPECIAL 70%   ",
            "codigo_obra_social": "83                  "
        },
        {
            "codigo": "922                 ",
            "nombre": "OSPIM - AMTIMA                ",
            "codigo_obra_social": "69                  "
        },
        {
            "codigo": "921                 ",
            "nombre": "SWISS PMO DIABETICOS INSULINAS",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "920                 ",
            "nombre": "SWISS PMO ANTIRETRO-VIRAL",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "919                 ",
            "nombre": "CAJA ABOGADOS PMI             ",
            "codigo_obra_social": "17                  "
        },
        {
            "codigo": "917                 ",
            "nombre": "HERCULES INSULINAS            ",
            "codigo_obra_social": "38                  "
        },
        {
            "codigo": "915                 ",
            "nombre": "HERCULES HIPUGLUCEMIENTES     ",
            "codigo_obra_social": "38                  "
        },
        {
            "codigo": "914                 ",
            "nombre": "MEDIFE PMI                    ",
            "codigo_obra_social": "45                  "
        },
        {
            "codigo": "913                 ",
            "nombre": "MEDIFE PLAN BRONCE            ",
            "codigo_obra_social": "45                  "
        },
        {
            "codigo": "912                 ",
            "nombre": "MEDIFE PLAN PLATA             ",
            "codigo_obra_social": "45                  "
        },
        {
            "codigo": "911                 ",
            "nombre": "MEDIFE PLAN AZUL              ",
            "codigo_obra_social": "45                  "
        },
        {
            "codigo": "907                 ",
            "nombre": "PERKINS PMI                   ",
            "codigo_obra_social": "82                  "
        },
        {
            "codigo": "906                 ",
            "nombre": "PERKINS DIABETES              ",
            "codigo_obra_social": "82                  "
        },
        {
            "codigo": "905                 ",
            "nombre": "PERKINS AMB                   ",
            "codigo_obra_social": "82                  "
        },
        {
            "codigo": "904                 ",
            "nombre": "DOCTHOS 70%                   ",
            "codigo_obra_social": "31                  "
        },
        {
            "codigo": "903                 ",
            "nombre": "DOCTHOS 65%                   ",
            "codigo_obra_social": "31                  "
        },
        {
            "codigo": "902                 ",
            "nombre": "DOCTHOS 30%                   ",
            "codigo_obra_social": "31                  "
        },
        {
            "codigo": "901                 ",
            "nombre": "ASAMEF EMI 3ª EDAD            ",
            "codigo_obra_social": "15                  "
        },
        {
            "codigo": "900                 ",
            "nombre": "ASAMEF EMI                    ",
            "codigo_obra_social": "15                  "
        },
        {
            "codigo": "895                 ",
            "nombre": "ANDAR PLAN PLUS               ",
            "codigo_obra_social": "10                  "
        },
        {
            "codigo": "891                 ",
            "nombre": "ANDAR PLAN ESPECIAL           ",
            "codigo_obra_social": "10                  "
        },
        {
            "codigo": "890                 ",
            "nombre": "ANDAR MONOTRIB CRONICOS RES310",
            "codigo_obra_social": "10                  "
        },
        {
            "codigo": "889                 ",
            "nombre": "ANDAR PLAN CLASICO            ",
            "codigo_obra_social": "10                  "
        },
        {
            "codigo": "887                 ",
            "nombre": "ANDAR MONOTRIB AMBULATOR      ",
            "codigo_obra_social": "10                  "
        },
        {
            "codigo": "871                 ",
            "nombre": "ASAMEF AÑOS DORADOS           ",
            "codigo_obra_social": "15                  "
        },
        {
            "codigo": "863                 ",
            "nombre": "OSPE AMBULATORIO 50           ",
            "codigo_obra_social": "62                  "
        },
        {
            "codigo": "862                 ",
            "nombre": "OSPE RESOL. ESPECIALES        ",
            "codigo_obra_social": "62                  "
        },
        {
            "codigo": "861                 ",
            "nombre": "OSPE PMI                      ",
            "codigo_obra_social": "62                  "
        },
        {
            "codigo": "860                 ",
            "nombre": "OSPE AMBULATORIO 40           ",
            "codigo_obra_social": "62                  "
        },
        {
            "codigo": "857                 ",
            "nombre": "OSMATA PLAN MED.INTEGRAL",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "856                 ",
            "nombre": "AMTTAC PMI                    ",
            "codigo_obra_social": "9                   "
        },
        {
            "codigo": "855                 ",
            "nombre": "AMTTAC MS-105                 ",
            "codigo_obra_social": "9                   "
        },
        {
            "codigo": "853                 ",
            "nombre": "OSPECOR PETROLEROS PMI        ",
            "codigo_obra_social": "64                  "
        },
        {
            "codigo": "851                 ",
            "nombre": "OSPECOR PETROLEROS AMBULAT    ",
            "codigo_obra_social": "64                  "
        },
        {
            "codigo": "850                 ",
            "nombre": "DAS PLAN PMI                  ",
            "codigo_obra_social": "28                  "
        },
        {
            "codigo": "849                 ",
            "nombre": "DAS PLAN NIÑOS                ",
            "codigo_obra_social": "28                  "
        },
        {
            "codigo": "848                 ",
            "nombre": "DAS PLAN ADULTOS              ",
            "codigo_obra_social": "28                  "
        },
        {
            "codigo": "847                 ",
            "nombre": "GEA PMI                       ",
            "codigo_obra_social": "36                  "
        },
        {
            "codigo": "846                 ",
            "nombre": "GEA MONOTRIBUTISTA            ",
            "codigo_obra_social": "36                  "
        },
        {
            "codigo": "845                 ",
            "nombre": "GEA PLUS/STAND SIN PE/PMI     ",
            "codigo_obra_social": "36                  "
        },
        {
            "codigo": "844                 ",
            "nombre": "GEA GOLD/TERRA/MASTER         ",
            "codigo_obra_social": "36                  "
        },
        {
            "codigo": "840                 ",
            "nombre": "MET MTA - MTB",
            "codigo_obra_social": "46                  "
        },
        {
            "codigo": "836                 ",
            "nombre": "OMINT PLAN F-LINEA F",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "834                 ",
            "nombre": "OMINT PLAN INFANTIL",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "833                 ",
            "nombre": "OSDOP                         ",
            "codigo_obra_social": "53                  "
        },
        {
            "codigo": "828                 ",
            "nombre": "OSTEL AMBULATORIO             ",
            "codigo_obra_social": "76                  "
        },
        {
            "codigo": "826                 ",
            "nombre": "OSTEL HIPOGLUCEMIANTES        ",
            "codigo_obra_social": "76                  "
        },
        {
            "codigo": "825                 ",
            "nombre": "OSTEL INSULINAS               ",
            "codigo_obra_social": "76                  "
        },
        {
            "codigo": "824                 ",
            "nombre": "OSPACA AMBU 03-04",
            "codigo_obra_social": "60                  "
        },
        {
            "codigo": "818                 ",
            "nombre": "VESALIO ONCOLOGICO 100%       ",
            "codigo_obra_social": "90                  "
        },
        {
            "codigo": "817                 ",
            "nombre": "VESALIO PMI 100%              ",
            "codigo_obra_social": "90                  "
        },
        {
            "codigo": "816                 ",
            "nombre": "VESALIO AMB 50%               ",
            "codigo_obra_social": "90                  "
        },
        {
            "codigo": "815                 ",
            "nombre": "VESALIO AMB 40%               ",
            "codigo_obra_social": "90                  "
        },
        {
            "codigo": "814                 ",
            "nombre": "MET MTARED - MTBRED",
            "codigo_obra_social": "46                  "
        },
        {
            "codigo": "813                 ",
            "nombre": "HERCULES PMI                  ",
            "codigo_obra_social": "38                  "
        },
        {
            "codigo": "802                 ",
            "nombre": "OSPIP ESPECIAL DIABETES",
            "codigo_obra_social": "70                  "
        },
        {
            "codigo": "801                 ",
            "nombre": "OSPIP PMI                     ",
            "codigo_obra_social": "70                  "
        },
        {
            "codigo": "800                 ",
            "nombre": "ACA SALUD PLAN 7              ",
            "codigo_obra_social": "3                   "
        },
        {
            "codigo": "761                 ",
            "nombre": "HOSPITAL PRIVADO CS MEDIMAX   ",
            "codigo_obra_social": "39                  "
        },
        {
            "codigo": "760                 ",
            "nombre": "HOSPITAL PRIVADO CS OPEN      ",
            "codigo_obra_social": "39                  "
        },
        {
            "codigo": "759                 ",
            "nombre": "HOSPITAL PRIVADO CS OPTIMO    ",
            "codigo_obra_social": "39                  "
        },
        {
            "codigo": "758                 ",
            "nombre": "FEDERADA SALUD INTERN AUTORIZ",
            "codigo_obra_social": "33                  "
        },
        {
            "codigo": "756                 ",
            "nombre": "OMINT CRONICOS",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "755                 ",
            "nombre": "OMINT PLAN MATERNAL",
            "codigo_obra_social": "48                  "
        },
        {
            "codigo": "746                 ",
            "nombre": "CRS-OSPOCE CT PMI             ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "744                 ",
            "nombre": "CRS-OSPOCE CA PMI             ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "742                 ",
            "nombre": "CRS-OSCEP CT PMI              ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "741                 ",
            "nombre": "CRS-OSCEP CT AMB              ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "740                 ",
            "nombre": "CRS-OSPOCE 45 PMI             ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "738                 ",
            "nombre": "CRS-OSCEP CA PMI              ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "737                 ",
            "nombre": "CRS-OSCEP CA AMB              ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "736                 ",
            "nombre": "CRS-OSPOCE 45 AMB             ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "733                 ",
            "nombre": "JERARQUICOS PL.MATERN.INFANTIL",
            "codigo_obra_social": "42                  "
        },
        {
            "codigo": "732                 ",
            "nombre": "JERARQUICOS PL-PMI 2886 AMBUL",
            "codigo_obra_social": "42                  "
        },
        {
            "codigo": "731                 ",
            "nombre": "JERARQUICOS PL-PMI 2000 AMB",
            "codigo_obra_social": "42                  "
        },
        {
            "codigo": "730                 ",
            "nombre": "JERARQUICOS PL-PMI AMBULATOR",
            "codigo_obra_social": "42                  "
        },
        {
            "codigo": "726                 ",
            "nombre": "OSME PLAN MEDICO 2            ",
            "codigo_obra_social": "58                  "
        },
        {
            "codigo": "719                 ",
            "nombre": "ANDAR CRONICO RES. 310 Y 758  ",
            "codigo_obra_social": "10                  "
        },
        {
            "codigo": "707                 ",
            "nombre": "APROSS PMI",
            "codigo_obra_social": "12                  "
        },
        {
            "codigo": "704                 ",
            "nombre": "APROSS AMBULATORIO",
            "codigo_obra_social": "12                  "
        },
        {
            "codigo": "704                 ",
            "nombre": "APROSS REFACTURADAS",
            "codigo_obra_social": "12                  "
        },
        {
            "codigo": "698                 ",
            "nombre": "OSITAC-AOITA AMBULATORIO      ",
            "codigo_obra_social": "56                  "
        },
        {
            "codigo": "697                 ",
            "nombre": "MEDICUS FAMILY CARE PLAN      ",
            "codigo_obra_social": "44                  "
        },
        {
            "codigo": "696                 ",
            "nombre": "MEDICUS CORPORATE             ",
            "codigo_obra_social": "44                  "
        },
        {
            "codigo": "695                 ",
            "nombre": "MEDICUS CORPORATE             ",
            "codigo_obra_social": "44                  "
        },
        {
            "codigo": "694                 ",
            "nombre": "MEDICUS CORPORATE MEDICAMENT  ",
            "codigo_obra_social": "44                  "
        },
        {
            "codigo": "693                 ",
            "nombre": "MEDICUS CORPORATE PL MIROT    ",
            "codigo_obra_social": "44                  "
        },
        {
            "codigo": "692                 ",
            "nombre": "MEDICUS CORPORATE PL.MIROT    ",
            "codigo_obra_social": "44                  "
        },
        {
            "codigo": "691                 ",
            "nombre": "MEDICUS CORPORATE PL.MIROT    ",
            "codigo_obra_social": "44                  "
        },
        {
            "codigo": "689                 ",
            "nombre": "MEDICUS MEDICAR BCO F.MAGIST  ",
            "codigo_obra_social": "44                  "
        },
        {
            "codigo": "688                 ",
            "nombre": "MEDICUS ONCOLOGICO            ",
            "codigo_obra_social": "44                  "
        },
        {
            "codigo": "687                 ",
            "nombre": "MEDICUS PLAN E                ",
            "codigo_obra_social": "44                  "
        },
        {
            "codigo": "686                 ",
            "nombre": "MEDICUS PLAN D                ",
            "codigo_obra_social": "44                  "
        },
        {
            "codigo": "685                 ",
            "nombre": "MEDICUS PLAN C                ",
            "codigo_obra_social": "44                  "
        },
        {
            "codigo": "684                 ",
            "nombre": "MEDICUS PLAN B                ",
            "codigo_obra_social": "44                  "
        },
        {
            "codigo": "683                 ",
            "nombre": "MEDICUS PLAN A                ",
            "codigo_obra_social": "44                  "
        },
        {
            "codigo": "674                 ",
            "nombre": "CRS-OSPOCE CT AMB             ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "672                 ",
            "nombre": "CRS-OSPOCE CA AMB             ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "668                 ",
            "nombre": "UNIMED OSPOCE PLAN ARRAYAN PMI",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "667                 ",
            "nombre": "UNIMED OSPOCE PLAN ARRAYAN AMB",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "666                 ",
            "nombre": "CRS-350 PMI                   ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "665                 ",
            "nombre": "CRS-350 AMB                   ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "663                 ",
            "nombre": "SWISS PLAN MATERNAL",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "644                 ",
            "nombre": "COMPLEMED HIPOGLUCEMIANTES    ",
            "codigo_obra_social": "24                  "
        },
        {
            "codigo": "638                 ",
            "nombre": "CRS-ROMAGOSA-PMI              ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "635                 ",
            "nombre": "COMPLEMED PMI                 ",
            "codigo_obra_social": "24                  "
        },
        {
            "codigo": "634                 ",
            "nombre": "COMPLEMED INSULINAS           ",
            "codigo_obra_social": "24                  "
        },
        {
            "codigo": "633                 ",
            "nombre": "COMPLEMED AMB                 ",
            "codigo_obra_social": "24                  "
        },
        {
            "codigo": "632                 ",
            "nombre": "HOSPITAL PRIVADO EMBARAZADA   ",
            "codigo_obra_social": "39                  "
        },
        {
            "codigo": "629                 ",
            "nombre": "HOSPITAL PRIVADO OSCA90       ",
            "codigo_obra_social": "39                  "
        },
        {
            "codigo": "628                 ",
            "nombre": "HOSPITAL PRIVADO PMI AUTORIZ  ",
            "codigo_obra_social": "39                  "
        },
        {
            "codigo": "627                 ",
            "nombre": "HOSPITAL PRIVADO AMB 50%      ",
            "codigo_obra_social": "39                  "
        },
        {
            "codigo": "625                 ",
            "nombre": "OSPIM USIMRA PMO              ",
            "codigo_obra_social": "69                  "
        },
        {
            "codigo": "624                 ",
            "nombre": "OSPIM USIMRA AMB              ",
            "codigo_obra_social": "69                  "
        },
        {
            "codigo": "622                 ",
            "nombre": "CRS-ROMAGOSA-AMB              ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "615                 ",
            "nombre": "OSECAC AUTORIZADO 100%        ",
            "codigo_obra_social": "54                  "
        },
        {
            "codigo": "613                 ",
            "nombre": "OSSEG SEGUROS PLAN INTEGRAL   ",
            "codigo_obra_social": "75                  "
        },
        {
            "codigo": "612                 ",
            "nombre": "OSSEG SEGUROS PLAN MAYOR      ",
            "codigo_obra_social": "75                  "
        },
        {
            "codigo": "611                 ",
            "nombre": "OSSEG SEGUROS PLAN ESPECIAL   ",
            "codigo_obra_social": "75                  "
        },
        {
            "codigo": "610                 ",
            "nombre": "OSSEG SEGUROS PLAN SALUD      ",
            "codigo_obra_social": "75                  "
        },
        {
            "codigo": "609                 ",
            "nombre": "OSSEG SEGUROS PLAN BASICO     ",
            "codigo_obra_social": "75                  "
        },
        {
            "codigo": "598                 ",
            "nombre": "SWISS MEDICAL AMBULAT",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "595                 ",
            "nombre": "SWISS PMO ONCOLOGICOS",
            "codigo_obra_social": "100                 "
        },
        {
            "codigo": "588                 ",
            "nombre": "OSPATCA  PMI AUTORIZADO       ",
            "codigo_obra_social": "61                  "
        },
        {
            "codigo": "587                 ",
            "nombre": "OSPATCA  ONCOLOG AUTORIZADO   ",
            "codigo_obra_social": "61                  "
        },
        {
            "codigo": "586                 ",
            "nombre": "OSPATCA  AMB COMUN            ",
            "codigo_obra_social": "61                  "
        },
        {
            "codigo": "582                 ",
            "nombre": "OSDIPP PMI                    ",
            "codigo_obra_social": "52                  "
        },
        {
            "codigo": "581                 ",
            "nombre": "OSDIPP ONCOLOGICO AUTORIZAD   ",
            "codigo_obra_social": "52                  "
        },
        {
            "codigo": "580                 ",
            "nombre": "OSDIPP PLAN 250               ",
            "codigo_obra_social": "52                  "
        },
        {
            "codigo": "579                 ",
            "nombre": "OSDIPP PLAN 2 Y 200           ",
            "codigo_obra_social": "52                  "
        },
        {
            "codigo": "578                 ",
            "nombre": "OSDIPP PLAN 150               ",
            "codigo_obra_social": "52                  "
        },
        {
            "codigo": "577                 ",
            "nombre": "OSDIPP PLAN 1 Y 100           ",
            "codigo_obra_social": "52                  "
        },
        {
            "codigo": "576                 ",
            "nombre": "OSDIPP PLAN MAGNUS            ",
            "codigo_obra_social": "52                  "
        },
        {
            "codigo": "575                 ",
            "nombre": "OSDIPP PLAN 350               ",
            "codigo_obra_social": "52                  "
        },
        {
            "codigo": "574                 ",
            "nombre": "OSDIPP PLAN 3 Y 300           ",
            "codigo_obra_social": "52                  "
        },
        {
            "codigo": "573                 ",
            "nombre": "OSDIPP PLAN 4                 ",
            "codigo_obra_social": "52                  "
        },
        {
            "codigo": "572                 ",
            "nombre": "OSDIPP PLAM PMO               ",
            "codigo_obra_social": "52                  "
        },
        {
            "codigo": "569                 ",
            "nombre": "OSPEC PMI SET-SALUD           ",
            "codigo_obra_social": "63                  "
        },
        {
            "codigo": "568                 ",
            "nombre": "OSPEC AMBULAT SET-SALUD       ",
            "codigo_obra_social": "63                  "
        },
        {
            "codigo": "567                 ",
            "nombre": "DIBA HIPOGLUC. ORAL           ",
            "codigo_obra_social": "29                  "
        },
        {
            "codigo": "566                 ",
            "nombre": "DIBA LECHES                   ",
            "codigo_obra_social": "29                  "
        },
        {
            "codigo": "565                 ",
            "nombre": "COB.MED.CORDOBA AUT.ESPEC     ",
            "codigo_obra_social": "21                  "
        },
        {
            "codigo": "564                 ",
            "nombre": "COB.MED.CORDOBA PMI           ",
            "codigo_obra_social": "21                  "
        },
        {
            "codigo": "559                 ",
            "nombre": "COB.MED.CORDOBA 60%           ",
            "codigo_obra_social": "21                  "
        },
        {
            "codigo": "557                 ",
            "nombre": "COB.MED.CORDOBA 40%           ",
            "codigo_obra_social": "21                  "
        },
        {
            "codigo": "556                 ",
            "nombre": "OSYC PMI PLAN CORAL           ",
            "codigo_obra_social": "79                  "
        },
        {
            "codigo": "555                 ",
            "nombre": "OSYC PMI PLAN MAR             ",
            "codigo_obra_social": "79                  "
        },
        {
            "codigo": "554                 ",
            "nombre": "OSYC AMB PLAN CORAL           ",
            "codigo_obra_social": "79                  "
        },
        {
            "codigo": "553                 ",
            "nombre": "OSYC AMB PLAN MAR             ",
            "codigo_obra_social": "79                  "
        },
        {
            "codigo": "552                 ",
            "nombre": "OSYC AMB PLAN NACAR           ",
            "codigo_obra_social": "79                  "
        },
        {
            "codigo": "551                 ",
            "nombre": "OSYC PMI PLAN NACAR           ",
            "codigo_obra_social": "79                  "
        },
        {
            "codigo": "548                 ",
            "nombre": "CRS-JOVEN PMI                 ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "546                 ",
            "nombre": "CRS-2000 PMI                  ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "543                 ",
            "nombre": "UNIMED OSPOCE PLAN CEIBO PMI",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "542                 ",
            "nombre": "UNIMED OSPOCE PLAN ROBLE PMI",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "540                 ",
            "nombre": "CRS-JOVEN AMB                 ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "538                 ",
            "nombre": "CRS-2000 AMB                  ",
            "codigo_obra_social": "27                  "
        },
        {
            "codigo": "534                 ",
            "nombre": "UNIMED OSPOCE PLAN CEIBO AMB",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "533                 ",
            "nombre": "UNIMED OSPOCE PLAN ROBLE AMB",
            "codigo_obra_social": "104                 "
        },
        {
            "codigo": "525                 ",
            "nombre": "POLICIA FEDERAL INTERNACION   ",
            "codigo_obra_social": "84                  "
        },
        {
            "codigo": "518                 ",
            "nombre": "HERCULES BASICO               ",
            "codigo_obra_social": "38                  "
        },
        {
            "codigo": "517                 ",
            "nombre": "SANAR PLAN 80  TRAT.PROLONG.  ",
            "codigo_obra_social": "88                  "
        },
        {
            "codigo": "516                 ",
            "nombre": "SANAR PLAN 10 TRAT.PROLONG.   ",
            "codigo_obra_social": "88                  "
        },
        {
            "codigo": "515                 ",
            "nombre": "SANAR PLAN Z TRAT.PROLONG.    ",
            "codigo_obra_social": "88                  "
        },
        {
            "codigo": "514                 ",
            "nombre": "SANAR PLAN 100 TRAT.PROLONG.  ",
            "codigo_obra_social": "88                  "
        },
        {
            "codigo": "513                 ",
            "nombre": "SANAR PLAN 80 E TRAT.PROLONG. ",
            "codigo_obra_social": "88                  "
        },
        {
            "codigo": "512                 ",
            "nombre": "SANAR PLAN 80 J TRAT.PROLONG. ",
            "codigo_obra_social": "88                  "
        },
        {
            "codigo": "511                 ",
            "nombre": "SANAR PLAN 50 TRAT.PROLONG.   ",
            "codigo_obra_social": "88                  "
        },
        {
            "codigo": "510                 ",
            "nombre": "SANAR PLAN 30 TRAT.PROLONG.   ",
            "codigo_obra_social": "88                  "
        },
        {
            "codigo": "509                 ",
            "nombre": "SANAR PLAN 10                 ",
            "codigo_obra_social": "88                  "
        },
        {
            "codigo": "508                 ",
            "nombre": "SANAR PLAN Z                  ",
            "codigo_obra_social": "88                  "
        },
        {
            "codigo": "507                 ",
            "nombre": "SANAR PLAN 100                ",
            "codigo_obra_social": "88                  "
        },
        {
            "codigo": "506                 ",
            "nombre": "SANAR PLAN 80 E               ",
            "codigo_obra_social": "88                  "
        },
        {
            "codigo": "505                 ",
            "nombre": "SANAR PLAN 80 J               ",
            "codigo_obra_social": "88                  "
        },
        {
            "codigo": "504                 ",
            "nombre": "SANAR PLAN 80                 ",
            "codigo_obra_social": "88                  "
        },
        {
            "codigo": "503                 ",
            "nombre": "SANAR PLAN 50                 ",
            "codigo_obra_social": "88                  "
        },
        {
            "codigo": "502                 ",
            "nombre": "SANAR PLAN 30                 ",
            "codigo_obra_social": "88                  "
        },
        {
            "codigo": "495                 ",
            "nombre": "UNION PERSONAL SIDA AUTORIZ",
            "codigo_obra_social": "103                 "
        },
        {
            "codigo": "494                 ",
            "nombre": "UNION PERSONAL ONCOL.AUTOR",
            "codigo_obra_social": "103                 "
        },
        {
            "codigo": "493                 ",
            "nombre": "UNION PERSONAL PMI",
            "codigo_obra_social": "103                 "
        },
        {
            "codigo": "492                 ",
            "nombre": "UNION PERSONAL ACCORD GUBERN",
            "codigo_obra_social": "103                 "
        },
        {
            "codigo": "491                 ",
            "nombre": "UNION PERSONAL ACCORD",
            "codigo_obra_social": "103                 "
        },
        {
            "codigo": "490                 ",
            "nombre": "UNION PERSONAL MAYORES",
            "codigo_obra_social": "103                 "
        },
        {
            "codigo": "489                 ",
            "nombre": "UNION PERSONAL ADHERENTE",
            "codigo_obra_social": "103                 "
        },
        {
            "codigo": "488                 ",
            "nombre": "UNION PERSONAL",
            "codigo_obra_social": "103                 "
        },
        {
            "codigo": "486                 ",
            "nombre": "COB.MED.CORDOBA LECHES        ",
            "codigo_obra_social": "21                  "
        },
        {
            "codigo": "485                 ",
            "nombre": "IMG OSPILM PMI                ",
            "codigo_obra_social": "96                  "
        },
        {
            "codigo": "484                 ",
            "nombre": "IMG OSPILM AMBULATORIO        ",
            "codigo_obra_social": "96                  "
        },
        {
            "codigo": "483                 ",
            "nombre": "IMG OS TECN FUTBOL PMI        ",
            "codigo_obra_social": "96                  "
        },
        {
            "codigo": "482                 ",
            "nombre": "IMG OS TECN FUTBOL AMBUL      ",
            "codigo_obra_social": "96                  "
        },
        {
            "codigo": "481                 ",
            "nombre": "IMG OSPFP PMI                 ",
            "codigo_obra_social": "96                  "
        },
        {
            "codigo": "480                 ",
            "nombre": "IMG OSPFP AMBULATORIO         ",
            "codigo_obra_social": "96                  "
        },
        {
            "codigo": "479                 ",
            "nombre": "IMG OSEIV PMI                 ",
            "codigo_obra_social": "96                  "
        },
        {
            "codigo": "478                 ",
            "nombre": "IMG OSEIV AMBULATORIO         ",
            "codigo_obra_social": "96                  "
        },
        {
            "codigo": "477                 ",
            "nombre": "IMG OSECA PMI                 ",
            "codigo_obra_social": "96                  "
        },
        {
            "codigo": "476                 ",
            "nombre": "IMG OSECA AMBULATORIO         ",
            "codigo_obra_social": "96                  "
        },
        {
            "codigo": "475                 ",
            "nombre": "IMG OSPIP PMI                 ",
            "codigo_obra_social": "96                  "
        },
        {
            "codigo": "474                 ",
            "nombre": "IMG OSPIP AMBULATORIO         ",
            "codigo_obra_social": "96                  "
        },
        {
            "codigo": "467                 ",
            "nombre": "PRENSA AMB                    ",
            "codigo_obra_social": "86                  "
        },
        {
            "codigo": "465                 ",
            "nombre": "OSPIL AMBULATORIO",
            "codigo_obra_social": "68                  "
        },
        {
            "codigo": "434                 ",
            "nombre": "DOCTHOS 60%                   ",
            "codigo_obra_social": "31                  "
        },
        {
            "codigo": "433                 ",
            "nombre": "DOCTHOS 50%                   ",
            "codigo_obra_social": "31                  "
        },
        {
            "codigo": "432                 ",
            "nombre": "DOCTHOS 40%                   ",
            "codigo_obra_social": "31                  "
        },
        {
            "codigo": "427                 ",
            "nombre": "PODER JUDICIAL PMI            ",
            "codigo_obra_social": "83                  "
        },
        {
            "codigo": "426                 ",
            "nombre": "PODER JUDICIAL AMBUL 60%      ",
            "codigo_obra_social": "83                  "
        },
        {
            "codigo": "424                 ",
            "nombre": "JERARQUICOS PLAN C AMBULAT",
            "codigo_obra_social": "42                  "
        },
        {
            "codigo": "423                 ",
            "nombre": "OSPRERA AMB MONOTRIBUTISTA    ",
            "codigo_obra_social": "74                  "
        },
        {
            "codigo": "422                 ",
            "nombre": "OSPRERA PMI RURAL             ",
            "codigo_obra_social": "74                  "
        },
        {
            "codigo": "421                 ",
            "nombre": "OSPRERA PMI MONOTRIBUTISTA    ",
            "codigo_obra_social": "74                  "
        },
        {
            "codigo": "420                 ",
            "nombre": "OSPRERA AMB RURAL             ",
            "codigo_obra_social": "74                  "
        },
        {
            "codigo": "419                 ",
            "nombre": "OSPLAD LECHES AUTORIZADAS     ",
            "codigo_obra_social": "72                  "
        },
        {
            "codigo": "418                 ",
            "nombre": "OSPLAD PMI                    ",
            "codigo_obra_social": "72                  "
        },
        {
            "codigo": "417                 ",
            "nombre": "OSPLAD AMBULATORIO            ",
            "codigo_obra_social": "72                  "
        },
        {
            "codigo": "410                 ",
            "nombre": "CERAMISTAS PMI (COLEG.FARMA)  ",
            "codigo_obra_social": "20                  "
        },
        {
            "codigo": "409                 ",
            "nombre": "CERAMISTAS AMB (COLEG.FARMA)  ",
            "codigo_obra_social": "20                  "
        },
        {
            "codigo": "373                 ",
            "nombre": "OSSEG SEGUROS PMI             ",
            "codigo_obra_social": "75                  "
        },
        {
            "codigo": "359                 ",
            "nombre": "OSPIP (IND.PLASTICO) AMB",
            "codigo_obra_social": "70                  "
        },
        {
            "codigo": "357                 ",
            "nombre": "OSTV                          ",
            "codigo_obra_social": "78                  "
        },
        {
            "codigo": "356                 ",
            "nombre": "COB.MED.CORDOBA 50%           ",
            "codigo_obra_social": "21                  "
        },
        {
            "codigo": "353                 ",
            "nombre": "OSMATA LECHES",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "350                 ",
            "nombre": "OSPIV PMI (VITAL)",
            "codigo_obra_social": "71                  "
        },
        {
            "codigo": "349                 ",
            "nombre": "OSPIV AMB (VITAL)",
            "codigo_obra_social": "71                  "
        },
        {
            "codigo": "340                 ",
            "nombre": "OSPIM PMI                     ",
            "codigo_obra_social": "69                  "
        },
        {
            "codigo": "339                 ",
            "nombre": "OSPIM AMB                     ",
            "codigo_obra_social": "69                  "
        },
        {
            "codigo": "338                 ",
            "nombre": "OSPAGA PMI",
            "codigo_obra_social": "96                  "
        },
        {
            "codigo": "337                 ",
            "nombre": "OSPAGA AMBULATORIO",
            "codigo_obra_social": "96                  "
        },
        {
            "codigo": "333                 ",
            "nombre": "OSIM INFANTIL                 ",
            "codigo_obra_social": "55                  "
        },
        {
            "codigo": "332                 ",
            "nombre": "OSTIG PMI                     ",
            "codigo_obra_social": "77                  "
        },
        {
            "codigo": "331                 ",
            "nombre": "OSTIG AMBULATORIO             ",
            "codigo_obra_social": "77                  "
        },
        {
            "codigo": "329                 ",
            "nombre": "OSPEC ESPEC.AUTO.ENCOTESA     ",
            "codigo_obra_social": "63                  "
        },
        {
            "codigo": "328                 ",
            "nombre": "OSPEC LECHES ENCOTESA         ",
            "codigo_obra_social": "63                  "
        },
        {
            "codigo": "327                 ",
            "nombre": "OSPEC PMI (ROSA)              ",
            "codigo_obra_social": "63                  "
        },
        {
            "codigo": "326                 ",
            "nombre": "OSPEC INTER.AUTO.ENCOTESA     ",
            "codigo_obra_social": "63                  "
        },
        {
            "codigo": "325                 ",
            "nombre": "OSPEC AMBULATO.ENCOTESA       ",
            "codigo_obra_social": "63                  "
        },
        {
            "codigo": "318                 ",
            "nombre": "OSECAC PMI                    ",
            "codigo_obra_social": "54                  "
        },
        {
            "codigo": "316                 ",
            "nombre": "OSTEL PMI 100%                ",
            "codigo_obra_social": "76                  "
        },
        {
            "codigo": "310                 ",
            "nombre": "OSPIL PMI                     ",
            "codigo_obra_social": "68                  "
        },
        {
            "codigo": "307                 ",
            "nombre": "OSAM PARTOS AUTORIZADOS       ",
            "codigo_obra_social": "50                  "
        },
        {
            "codigo": "306                 ",
            "nombre": "OSAM ESPECIALES AUTORIZADOS   ",
            "codigo_obra_social": "50                  "
        },
        {
            "codigo": "305                 ",
            "nombre": "OSAM PMI                      ",
            "codigo_obra_social": "50                  "
        },
        {
            "codigo": "304                 ",
            "nombre": "OSAM INTERNADO                ",
            "codigo_obra_social": "50                  "
        },
        {
            "codigo": "302                 ",
            "nombre": "OSAM                          ",
            "codigo_obra_social": "50                  "
        },
        {
            "codigo": "296                 ",
            "nombre": "DIBA AMBULATORIO",
            "codigo_obra_social": "29                  "
        },
        {
            "codigo": "281                 ",
            "nombre": "OSTIN SALUD INTERNADOS        ",
            "codigo_obra_social": "77                  "
        },
        {
            "codigo": "280                 ",
            "nombre": "OSTIN SALUD                   ",
            "codigo_obra_social": "77                  "
        },
        {
            "codigo": "274                 ",
            "nombre": "OSME PLAN MAT. INFANTIL       ",
            "codigo_obra_social": "58                  "
        },
        {
            "codigo": "242                 ",
            "nombre": "PRENSALUD PMI                 ",
            "codigo_obra_social": "86                  "
        },
        {
            "codigo": "241                 ",
            "nombre": "OSME INTERNADO                ",
            "codigo_obra_social": "58                  "
        },
        {
            "codigo": "232                 ",
            "nombre": "OSME LECHES                   ",
            "codigo_obra_social": "58                  "
        },
        {
            "codigo": "231                 ",
            "nombre": "OSME AMBULATORIO              ",
            "codigo_obra_social": "58                  "
        },
        {
            "codigo": "224                 ",
            "nombre": "DOULOS INTERNADOS             ",
            "codigo_obra_social": "32                  "
        },
        {
            "codigo": "217                 ",
            "nombre": "DOULOS AMBULATORIO DORADO     ",
            "codigo_obra_social": "32                  "
        },
        {
            "codigo": "216                 ",
            "nombre": "DOULOS AMBULATORIO PLATA      ",
            "codigo_obra_social": "32                  "
        },
        {
            "codigo": "215                 ",
            "nombre": "DOULOS AMBULATORIO AZUL       ",
            "codigo_obra_social": "32                  "
        },
        {
            "codigo": "205                 ",
            "nombre": "PRENSALUD AMBULATORIO         ",
            "codigo_obra_social": "86                  "
        },
        {
            "codigo": "189                 ",
            "nombre": "ASAMEF CARUSO                 ",
            "codigo_obra_social": "15                  "
        },
        {
            "codigo": "179                 ",
            "nombre": "IOSE HEMOFILIA 100% C/AUTORIZ ",
            "codigo_obra_social": "40                  "
        },
        {
            "codigo": "177                 ",
            "nombre": "IOSE HEMOFILIA 100 % S/AUTORIZ",
            "codigo_obra_social": "40                  "
        },
        {
            "codigo": "175                 ",
            "nombre": "IOSE HEMODIALISIS 100%        ",
            "codigo_obra_social": "40                  "
        },
        {
            "codigo": "173                 ",
            "nombre": "IOSE CARDIOVASCULAR 100%      ",
            "codigo_obra_social": "40                  "
        },
        {
            "codigo": "171                 ",
            "nombre": "IOSE AMB (CIE)                ",
            "codigo_obra_social": "40                  "
        },
        {
            "codigo": "168                 ",
            "nombre": "IOSE AMB (CIE)C/AUTORIZACION  ",
            "codigo_obra_social": "40                  "
        },
        {
            "codigo": "167                 ",
            "nombre": "PAMI ONCOLOGICO",
            "codigo_obra_social": "80                  "
        },
        {
            "codigo": "154                 ",
            "nombre": "OSMATA PLAN MAT.INFANTIL",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "153                 ",
            "nombre": "OSMATA PLAN MED.OBLIGATORIO",
            "codigo_obra_social": "57                  "
        },
        {
            "codigo": "143                 ",
            "nombre": "FIAT AMBULATORIO              ",
            "codigo_obra_social": "34                  "
        },
        {
            "codigo": "141                 ",
            "nombre": "ISSARA 50%                    ",
            "codigo_obra_social": "41                  "
        },
        {
            "codigo": "140                 ",
            "nombre": "ISSARA INTERN. C/AUTORIZA 100%",
            "codigo_obra_social": "41                  "
        },
        {
            "codigo": "139                 ",
            "nombre": "ISSARA ESPECIALES AUTORIZ 100%",
            "codigo_obra_social": "41                  "
        },
        {
            "codigo": "138                 ",
            "nombre": "ISSARA ONCOLOGIC C/AUTOR.100% ",
            "codigo_obra_social": "41                  "
        },
        {
            "codigo": "132                 ",
            "nombre": "PRENSA ONCOLOGICO AUTORIZADO  ",
            "codigo_obra_social": "86                  "
        },
        {
            "codigo": "129                 ",
            "nombre": "DIBPFA PMI",
            "codigo_obra_social": "30                  "
        },
        {
            "codigo": "125                 ",
            "nombre": "CAJA ABOGADOS AMBULATORIO 80% ",
            "codigo_obra_social": "17                  "
        },
        {
            "codigo": "121                 ",
            "nombre": "ATSA AMBULATORIO              ",
            "codigo_obra_social": "16                  "
        },
        {
            "codigo": "114                 ",
            "nombre": "PRENSA INTERNADOS             ",
            "codigo_obra_social": "86                  "
        },
        {
            "codigo": "100%                ",
            "nombre": "100%",
            "codigo_obra_social": "CARDINAL            "
        },
        {
            "codigo": "91                  ",
            "nombre": "OSDE-CRONICO-GERENFAR INTERIO ",
            "codigo_obra_social": "51                  "
        },
        {
            "codigo": "90                  ",
            "nombre": "OSDE-MI-GERENFAR INTERIOR     ",
            "codigo_obra_social": "51                  "
        },
        {
            "codigo": "88                  ",
            "nombre": "OSDE-AMBU -GERENFAR INTERIOR- ",
            "codigo_obra_social": "51                  "
        },
        {
            "codigo": "64                  ",
            "nombre": "ISSARA P.M.I C/AUTORIZAC 100% ",
            "codigo_obra_social": "41                  "
        },
        {
            "codigo": "62                  ",
            "nombre": "IOSE AMBULATORIO",
            "codigo_obra_social": "40                  "
        },
        {
            "codigo": "61                  ",
            "nombre": "FIAT PMI                      ",
            "codigo_obra_social": "34                  "
        },
        {
            "codigo": "57                  ",
            "nombre": "ATSA PMI                      ",
            "codigo_obra_social": "16                  "
        },
        {
            "codigo": "55                  ",
            "nombre": "DIBA INTERNADO                ",
            "codigo_obra_social": "29                  "
        },
        {
            "codigo": "52                  ",
            "nombre": "OSTEL AZUL Y AZUL             ",
            "codigo_obra_social": "76                  "
        },
        {
            "codigo": "50                  ",
            "nombre": "CAJA NOTARIAL AMBULATORIO     ",
            "codigo_obra_social": "18                  "
        },
        {
            "codigo": "48                  ",
            "nombre": "HERCULES GENERAL              ",
            "codigo_obra_social": "38                  "
        },
        {
            "codigo": "46                  ",
            "nombre": "CAJA ABOGADOS AMBULATORIO 50% ",
            "codigo_obra_social": "17                  "
        },
        {
            "codigo": "45                  ",
            "nombre": "CAJA ABOGADOS ONCOLOGICOS     ",
            "codigo_obra_social": "17                  "
        },
        {
            "codigo": "44                  ",
            "nombre": "OSECAC JUBILADO",
            "codigo_obra_social": "54                  "
        },
        {
            "codigo": "40%                 ",
            "nombre": "40%",
            "codigo_obra_social": "CARDINAL            "
        },
        {
            "codigo": "37                  ",
            "nombre": "PRENSA PMI                    ",
            "codigo_obra_social": "86                  "
        },
        {
            "codigo": "35                  ",
            "nombre": "ATSA INTERNADO                ",
            "codigo_obra_social": "16                  "
        },
        {
            "codigo": "34                  ",
            "nombre": "DIBPFA AMBULATORIO",
            "codigo_obra_social": "30                  "
        },
        {
            "codigo": "32                  ",
            "nombre": "ACA SALUD PLAN 21 A.CORPORAT  ",
            "codigo_obra_social": "3                   "
        },
        {
            "codigo": "29                  ",
            "nombre": "ACA SALUD PLAN 7A             ",
            "codigo_obra_social": "3                   "
        },
        {
            "codigo": "28                  ",
            "nombre": "ACA SALUD PLAN 21             ",
            "codigo_obra_social": "3                   "
        },
        {
            "codigo": "27                  ",
            "nombre": "ACA SALUD PMI                 ",
            "codigo_obra_social": "3                   "
        },
        {
            "codigo": "26M                 ",
            "nombre": "PAMI AMBU MANUAL",
            "codigo_obra_social": "PAMIMANUAL          "
        },
        {
            "codigo": "26                  ",
            "nombre": "PAMI AMBU",
            "codigo_obra_social": "80                  "
        },
        {
            "codigo": "22                  ",
            "nombre": "OSECAC ACTIVO",
            "codigo_obra_social": "54                  "
        },
        {
            "codigo": "03                  ",
            "nombre": "PMI 100%",
            "codigo_obra_social": "DASUTEN             "
        },
        {
            "codigo": "02                  ",
            "nombre": "PLAN BA 30%",
            "codigo_obra_social": "MPN                 "
        },
        {
            "codigo": "01                  ",
            "nombre": "PLAN SF 30%",
            "codigo_obra_social": "MPN                 "
        },
        {
            "codigo": "01                  ",
            "nombre": "IOSFAAMBULATORIO",
            "codigo_obra_social": "106                 "
        },
        {
            "codigo": "01                  ",
            "nombre": "REFACTURADAS",
            "codigo_obra_social": "84                  "
        }
    ]


def run(session: Session) -> None:
    """
    Inserta/actualiza Planes.
    - activo=True siempre
    - resuelve FK por obra_social.codigo
    - upsert por plan.codigo (debe ser unique)
    """
    # cache de obras sociales por codigo
    codigos_os = sorted({_norm(p["codigo_obra_social"]) for p in PLANES if _norm(p["codigo_obra_social"])})
    obras = session.execute(
        select(ObraSocial).where(ObraSocial.codigo.in_(codigos_os))
    ).scalars().all()
    obra_by_codigo = {o.codigo: o for o in obras}

    faltantes = [c for c in codigos_os if c not in obra_by_codigo]
    if faltantes:
        raise ValueError(
            "No existen estas obras sociales (obra_social.codigo) y son requeridas por planes:\n"
            + "\n".join(f"- {c}" for c in faltantes)
        )

    for p in PLANES:
        plan_codigo = _norm(p["codigo"])
        nombre = _norm(p["nombre"])
        os_codigo = _norm(p["codigo_obra_social"])

        obra = obra_by_codigo[os_codigo]

        existente = session.execute(
            select(Plan).where(
                and_(
                    Plan.obra_social_id == obra.obra_social_id,
                    Plan.codigo == plan_codigo,
                    Plan.nombre == nombre,
                )
            )
        ).scalar_one_or_none()
        if existente:
            existente.nombre = nombre  # o existente.nombre = desc
            existente.activo = True
            existente.obra_social_id = obra.obra_social_id
        else:
            nuevo = Plan(
                codigo=plan_codigo,
                nombre=nombre,
                activo=True,
                obra_social_id=obra.obra_social_id,
            )
            session.add(nuevo)

