      ******************************************************************
      * BANQUE HEXAGONE - SYSTEME CENTRAL Z/OS CORE BANKING            *
      * COPYBOOK : CBK_CUSTOMERS_REF.CPY                               *
      * OBJET    : EXTRACTION QUOTIDIENNE REFERENTIEL TIERS / CLIENTS  *
      * FORMAT   : RECFM=FB, LRECL=140 OCTETS (SANS SAUT DE LIGNE LF)  *
      * ENCODAGE : IBM EBCDIC CP500 + BINAIRE PACKED DECIMAL (COMP-3)  *
      * ENVELOPPE: 1ER BLOC '00CFT_HDR' / DERNIER BLOC '99CFT_TRL'     *
      ******************************************************************
       01  CBK-CUSTOMER-RECORD.
           05  CBK-CUST-ID               PIC X(12).
      *        OCTETS 001-012 (EBCDIC) : ID TIERS (EX: CUST00002026)
           05  CBK-CODE-AGENCE           PIC X(04).
      *        OCTETS 013-016 (EBCDIC) : CODE AGENCE ('0042' OU '42  ')
           05  CBK-CODE-GUICHET          PIC X(05).
      *        OCTETS 017-021 (EBCDIC) : CODE GUICHET ('00042' OU '42   ')
           05  CBK-CODE-REGION           PIC X(04).
      *        OCTETS 022-025 (EBCDIC) : DIRECTION REGIONALE (REG1..REG8)
           05  CBK-DATE-NAISSANCE        PIC X(08).
      *        OCTETS 026-033 (EBCDIC) : DATE NAISSANCE AAAAMMJJ
           05  CBK-AGE-COMP3             PIC S9(03) USAGE COMP-3.
      *        OCTETS 034-035 (2 OCTETS BINAIRE PACKED DECIMAL COMP-3) :
      *        3 CHIFFRES BCD + DEMI-OCTET SIGNE ('C'=+ / 'D'=-)
           05  CBK-SEG-CLIENTELE         PIC X(12).
      *        OCTETS 036-047 (EBCDIC) : SEGMENT COMMERCIAL
           05  CBK-DATE-ENTREE-REL       PIC X(08).
      *        OCTETS 048-055 (EBCDIC) : DATE ENTREE RELATION AAAAMMJJ
           05  CBK-DATE-CLOTURE-REL      PIC X(08).
      *        OCTETS 056-063 (EBCDIC) : DATE FIN RELATION (00000000)
           05  CBK-STATUT-DOSSIER        PIC X(06).
      *        OCTETS 064-069 (EBCDIC) : STATUT TIERS (ACTIF / CLOTUR)
           05  CBK-NOM-PATRONYMIQUE      PIC X(26).
      *        OCTETS 070-095 (EBCDIC) : NOM PATRONYMIQUE
           05  CBK-PRENOM-USUEL          PIC X(20).
      *        OCTETS 096-115 (EBCDIC) : PRENOM USUEL
           05  CBK-CSP-CODE              PIC X(10).
      *        OCTETS 116-125 (EBCDIC) : CODE CSP INTERNE
           05  CBK-DATE-MAJ-BATCH        PIC X(08).
      *        OCTETS 126-133 (EBCDIC) : DATE ARRETE BATCH AAAAMMJJ
           05  CBK-FILLER-ZOS            PIC X(07).
      *        OCTETS 134-140 (EBCDIC) : RESERVE EXPLOITATION Z/OS
