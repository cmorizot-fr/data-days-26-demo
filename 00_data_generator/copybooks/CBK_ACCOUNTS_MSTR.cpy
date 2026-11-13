      ******************************************************************
      * BANQUE HEXAGONE - SYSTEME CENTRAL Z/OS CORE BANKING            *
      * COPYBOOK : CBK_ACCOUNTS_MSTR.CPY                               *
      * OBJET    : REFERENTIEL MAITRE DES COMPTES COURANTS & LIVRETS   *
      * FORMAT   : RECFM=FB, LRECL=150 OCTETS (SANS SAUT DE LIGNE LF)  *
      * ENCODAGE : IBM EBCDIC CP500 + BINAIRE PACKED DECIMAL (COMP-3)  *
      * ENVELOPPE: 1ER BLOC '00CFT_HDR' / DERNIER BLOC '99CFT_TRL'     *
      ******************************************************************
       01  CBK-ACCOUNT-MASTER-RECORD.
           05  CBK-ACC-ID                PIC X(11).
      *        OCTETS 001-011 (EBCDIC) : ID INTERNE COMPTE (ACC00002026)
           05  CBK-NUM-COMPTE-11         PIC X(11).
      *        OCTETS 012-022 (EBCDIC) : NUMERO DE COMPTE RIB 11 CAR
           05  CBK-CUST-ID               PIC X(12).
      *        OCTETS 023-034 (EBCDIC) : ID TIERS TITULAIRE
           05  CBK-CODE-BANQUE           PIC X(05).
      *        OCTETS 035-039 (EBCDIC) : CODE BANQUE (30002)
           05  CBK-CODE-AGENCE           PIC X(04).
      *        OCTETS 040-043 (EBCDIC) : CODE AGENCE ('0042' OU '42  ')
           05  CBK-CODE-GUICHET          PIC X(05).
      *        OCTETS 044-048 (EBCDIC) : CODE GUICHET ('00042' OU '42   ')
           05  CBK-CLE-RIB               PIC 9(02).
      *        OCTETS 049-050 (EBCDIC) : CLE RIB (01 A 97)
           05  CBK-IBAN-FR27             PIC X(27).
      *        OCTETS 051-077 (EBCDIC) : IBAN ISO FRkk (27 CAR)
           05  CBK-TYPE-COMPTE           PIC X(10).
      *        OCTETS 078-087 (EBCDIC) : CC_CHQ, LIVRET_A, LDDS, LIV_MAISON
           05  CBK-DEVISE-ISO            PIC X(03).
      *        OCTETS 088-090 (EBCDIC) : DEVISE (EUR)
           05  CBK-DATE-OUVERTURE        PIC X(08).
      *        OCTETS 091-098 (EBCDIC) : DATE OUVERTURE AAAAMMJJ
           05  CBK-DATE-CLOTURE          PIC X(08).
      *        OCTETS 099-106 (EBCDIC) : DATE CLOTURE (00000000 SI ACTIF)
           05  CBK-STATUT-COMPTE         PIC X(06).
      *        OCTETS 107-112 (EBCDIC) : STATUT COMPTE (OUVERT)
           05  CBK-TAUX-REMUN-BPS        PIC S9(05) USAGE COMP-3.
      *        OCTETS 113-115 (3 OCTETS BINAIRE COMP-3) :
      *        TAUX EN POINTS DE BASE (5 CHIFFRES BCD + SIGNE 'C'/'D')
           05  CBK-SOLDE-VEILLE-COMP3    PIC S9(13)V99 USAGE COMP-3.
      *        OCTETS 116-123 (8 OCTETS BINAIRE COMP-3) :
      *        SOLDE COMPTABLE J-1 EN CENTIMES (15 CHIFFRES BCD + SIGNE
      *        'C'=CREDIT POSITIF / 'D'=DEBIT NEGATIF)
           05  CBK-DATE-DERNIER-MVT      PIC X(08).
      *        OCTETS 124-131 (EBCDIC) : DATE DERNIERE ECRITURE AAAAMMJJ
           05  CBK-LIBELLE-PRODUIT       PIC X(19).
      *        OCTETS 132-150 (EBCDIC) : LIBELLE PRODUIT
