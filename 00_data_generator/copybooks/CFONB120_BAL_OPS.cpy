      ******************************************************************
      * BANQUE HEXAGONE - SYSTEME CENTRAL Z/OS CORE BANKING            *
      * COPYBOOK : CFONB120_BAL_OPS.CPY                                *
      * OBJET    : RELEVES COMPTABLES MULTI-LIGNES CFONB 120 OCTETS    *
      * ENCODAGE : ISO-8859-15 (.cfonb.gz SUR 2025 / .cfonb SUR 2026)  *
      * ATTENTION EXPLOITATION :                                       *
      *   1) BANNIERES CFT EN DEBUT ('00') ET FIN ('99') DE FICHIER    *
      *      VERIFIER IMPERATIVEMENT 'RC=0000' SUR LE TRAILER '99'     *
      *      POUR ECARTER LES FICHIERS INTERROMPUS EN ABEND Z/OS !     *
      *   2) LES LIGNES COMPLEMENTAIRES '05' (BIC & END-TO-END SEPA)   *
      *      SUIVENT PHYSIQUEMENT LEUR LIGNE MOUVEMENT '04' PARENTE    *
      *      SANS REPETITION DU NUMERO D'ECRITURE !                    *
      ******************************************************************
       01  CFONB-120-LINE.
           05  CFONB-CODE-ENR            PIC X(02).
      *        POS 001-002 :
      *          '00' = BANNIERE EN-TETE TRANSFERT CFT (00CFT_HDR...)
      *          '01' = ANCIEN SOLDE DEBUT PERIODE
      *          '04' = MOUVEMENT COMPTABLE VALORISE J+1
      *          '05' = COMPLEMENT D'INFORMATION SEPA RATTACHE AU '04'
      *                 PRECEDENT DANS L'ORDRE PHYSIQUE DU FICHIER !
      *          '07' = NOUVEAU SOLDE FIN PERIODE
      *          '99' = TRAILER CONTROLE CFT (99CFT_TRL STATUS=... RC=..)

      *----------------------------------------------------------------*
      * STRUCTURE PRINCIPALE POUR CODE-ENR IN ('01', '04', '07')       *
      *----------------------------------------------------------------*
           05  CFONB-MAIN-BODY.
               10  CFONB-CODE-BANQUE     PIC X(05).
      *            POS 003-007 : CODE BANQUE (30002)
               10  CFONB-CODE-OP-INTERNE PIC X(04).
      *            POS 008-011 : '0000' SOLDE, '0420' SALAIRE, '0430' REMB
      *            '0580' VIR INTERNE 58*, '0810' VIR SEPA INST SORTANT,
      *            '0650' PRLV SEPA, '0310' CARTE BANCAIRE (SANS LIGNE 05)
               10  CFONB-CODE-GUICHET    PIC X(05).
      *            POS 012-016 : GUICHET AGENCE ('00042' OU '42   '/'     ')
               10  CFONB-CODE-DEVISE     PIC X(03).
      *            POS 017-019 : DEVISE (EUR)
               10  CFONB-NB-DECIMALES    PIC 9(01).
      *            POS 020-020 : DECIMALES (2)
               10  CFONB-ZONE-RES-1      PIC X(01).
      *            POS 021-021 : ESPACE
               10  CFONB-NUM-COMPTE      PIC X(11).
      *            POS 022-032 : NUMERO DE COMPTE 11 CARACTERES
               10  CFONB-CODE-AFB        PIC X(02).
      *            POS 033-034 : '60' SOLDE INIT, '62' SOLDE FIN,
      *            '05' VIR RECU, '16' VIR EMIS, '08' PRLV, '28' CB
               10  CFONB-DATE-COMPTA     PIC X(08).
      *            POS 035-042 : DATE COMPTABLE AAAAMMJJ
               10  CFONB-CODE-REJET      PIC X(02).
      *            POS 043-044 : '00'
               10  CFONB-DATE-VALEUR     PIC X(08).
      *            POS 045-052 : DATE DE VALEUR AAAAMMJJ
      *            ANOMALIE LEGACY CONNUE : '00000000' OU '99999999'
               10  CFONB-LIBELLE         PIC X(31).
      *            POS 053-083 : LIBELLE COURT 31 CARACTERES
               10  CFONB-ZONE-RES-2      PIC X(02).
      *            POS 084-085 : ESPACES
               10  CFONB-NUM-ECRITURE    PIC 9(07).
      *            POS 086-092 : SEQUENCE ECRITURE SUR 7 CHIFFRES
               10  CFONB-IND-EXO         PIC X(01).
      *            POS 093-093 : '0'
               10  CFONB-IND-INDISP      PIC X(01).
      *            POS 094-094 : '0'
               10  CFONB-MONTANT-SIGNE   PIC X(14).
      *            POS 095-108 : MONTANT EN CENTIMES SIGNE CFONB :
      *              POS 095-107 = 13 PREMIERS CHIFFRES
      *              POS 108     = UNITE + SIGNE :
      *                CREDIT (+) : '{'=0,'A'=1..'I'=9
      *                DEBIT  (-) : '}'=0,'J'=1..'R'=9
               10  CFONB-REF-TECH        PIC X(12).
      *            POS 109-120 : REFERENCE INTERNE LOT (HORS BIC SEPA)

      *----------------------------------------------------------------*
      * REDEFINITION POUR CODE-ENR = '05' (COMPLEMENT SEPA / MANDAT)   *
      *----------------------------------------------------------------*
           05  CFONB-COMPLEMENT-05 REDEFINES CFONB-MAIN-BODY.
               10  CF05-ENTETE-COMMUNE   PIC X(40).
      *            POS 003-042 : IDENTIQUE AU '04' PARENT (COMPTE/DATE)
               10  CF05-FILLER-1         PIC X(02).
      *            POS 043-044 : ESPACES
               10  CF05-QUALIFIANT       PIC X(03).
      *            POS 045-047 : 'IBI' (IDENTIFIANT BIC & END-TO-END)
               10  CF05-CONTREPARTIE-BIC PIC X(12).
      *            POS 048-059 : CODE BIC CONTREPARTIE (EX: REVOLT21XXX)
               10  CF05-END-TO-END-ID    PIC X(36).
      *            POS 060-095 : IDENTIFIANT BOUT-EN-BOUT ISO 20022
               10  CF05-MOTIF-SEPA       PIC X(25).
      *            POS 096-120 : MOTIF / COMPLEMENT LIBELLE SEPA
