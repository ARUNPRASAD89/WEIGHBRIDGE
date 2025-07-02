--
-- PostgreSQL database dump
--

-- Dumped from database version 17.5
-- Dumped by pg_dump version 17.5

-- Started on 2025-07-02 15:25:49

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET transaction_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- TOC entry 217 (class 1259 OID 16389)
-- Name: material; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.material (
    materialcode integer NOT NULL,
    materialname character varying(100) NOT NULL,
    materialdescription character varying(255)
);


ALTER TABLE public.material OWNER TO postgres;

--
-- TOC entry 218 (class 1259 OID 16392)
-- Name: material_materialcode_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.material_materialcode_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.material_materialcode_seq OWNER TO postgres;

--
-- TOC entry 4923 (class 0 OID 0)
-- Dependencies: 218
-- Name: material_materialcode_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.material_materialcode_seq OWNED BY public.material.materialcode;


--
-- TOC entry 219 (class 1259 OID 16393)
-- Name: shiftmaster; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.shiftmaster (
    shiftname character varying(50) NOT NULL,
    fromshift time without time zone,
    toshift time without time zone
);


ALTER TABLE public.shiftmaster OWNER TO postgres;

--
-- TOC entry 220 (class 1259 OID 16396)
-- Name: suppliers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.suppliers (
    suppliercode integer NOT NULL,
    suppliername character varying(100) NOT NULL,
    supplieraddress character varying(255),
    contactperson character varying(100),
    contactnumber character varying(20)
);


ALTER TABLE public.suppliers OWNER TO postgres;

--
-- TOC entry 221 (class 1259 OID 16399)
-- Name: suppliers_suppliercode_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.suppliers_suppliercode_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.suppliers_suppliercode_seq OWNER TO postgres;

--
-- TOC entry 4924 (class 0 OID 0)
-- Dependencies: 221
-- Name: suppliers_suppliercode_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.suppliers_suppliercode_seq OWNED BY public.suppliers.suppliercode;


--
-- TOC entry 228 (class 1259 OID 16450)
-- Name: templatefields; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.templatefields (
    templatename text NOT NULL,
    fieldname text NOT NULL,
    displayname text,
    x integer,
    y integer,
    width integer,
    height integer,
    fontname text,
    fontsize integer
);


ALTER TABLE public.templatefields OWNER TO postgres;

--
-- TOC entry 227 (class 1259 OID 16443)
-- Name: templatemaster; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.templatemaster (
    templatename text NOT NULL,
    ticketheight integer,
    ticketwidth integer,
    defaulttemplate boolean
);


ALTER TABLE public.templatemaster OWNER TO postgres;

--
-- TOC entry 222 (class 1259 OID 16400)
-- Name: tickets; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.tickets (
    "TicketNumber" integer NOT NULL,
    "VehicleNumber" character varying(50),
    "Date" date,
    "Time" time without time zone,
    "EmptyWeight" integer,
    "LoadedWeight" integer,
    "EmptyWeightDate" date,
    "EmptyWeightTime" time without time zone,
    "LoadWeightDate" date,
    "LoadWeightTime" time without time zone,
    "NetWeight" integer,
    "Pending" boolean,
    "Closed" boolean,
    "Exported" boolean,
    "Shift" character varying(2),
    "Materialname" character varying(255),
    "SupplierName" character varying(255),
    "State" character varying(50),
    "Blank" integer,
    "AMOUNT" integer,
    "STATUS" character varying(30),
    "EAMOUNT" integer,
    "LAMOUNT" integer,
    "TAMOUNT" integer,
    "NetWeight1" integer,
    "LWEIGHT" integer,
    "EWEIGHT" integer
);


ALTER TABLE public.tickets OWNER TO postgres;

--
-- TOC entry 223 (class 1259 OID 16405)
-- Name: usermanagement; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.usermanagement (
    userid integer NOT NULL,
    username character varying(50) NOT NULL,
    password character varying(50) NOT NULL,
    retypepasswd character varying(50),
    offlinetickets boolean DEFAULT false,
    deleterecords boolean DEFAULT false,
    duplicateticket boolean DEFAULT false,
    vehiclemaster boolean DEFAULT false,
    adminuser boolean DEFAULT false,
    primaryuser boolean DEFAULT false
);


ALTER TABLE public.usermanagement OWNER TO postgres;

--
-- TOC entry 224 (class 1259 OID 16414)
-- Name: usermanagement_userid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.usermanagement_userid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.usermanagement_userid_seq OWNER TO postgres;

--
-- TOC entry 4925 (class 0 OID 0)
-- Dependencies: 224
-- Name: usermanagement_userid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.usermanagement_userid_seq OWNED BY public.usermanagement.userid;


--
-- TOC entry 225 (class 1259 OID 16415)
-- Name: vehiclemaster; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vehiclemaster (
    vehicleid integer NOT NULL,
    vehiclenumber character varying(50) NOT NULL,
    vehicletareweight integer
);


ALTER TABLE public.vehiclemaster OWNER TO postgres;

--
-- TOC entry 226 (class 1259 OID 16418)
-- Name: vehiclemaster_vehicleid_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.vehiclemaster_vehicleid_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.vehiclemaster_vehicleid_seq OWNER TO postgres;

--
-- TOC entry 4926 (class 0 OID 0)
-- Dependencies: 226
-- Name: vehiclemaster_vehicleid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.vehiclemaster_vehicleid_seq OWNED BY public.vehiclemaster.vehicleid;


--
-- TOC entry 4726 (class 2604 OID 16419)
-- Name: material materialcode; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material ALTER COLUMN materialcode SET DEFAULT nextval('public.material_materialcode_seq'::regclass);


--
-- TOC entry 4727 (class 2604 OID 16420)
-- Name: suppliers suppliercode; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.suppliers ALTER COLUMN suppliercode SET DEFAULT nextval('public.suppliers_suppliercode_seq'::regclass);


--
-- TOC entry 4728 (class 2604 OID 16421)
-- Name: usermanagement userid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usermanagement ALTER COLUMN userid SET DEFAULT nextval('public.usermanagement_userid_seq'::regclass);


--
-- TOC entry 4735 (class 2604 OID 16422)
-- Name: vehiclemaster vehicleid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehiclemaster ALTER COLUMN vehicleid SET DEFAULT nextval('public.vehiclemaster_vehicleid_seq'::regclass);


--
-- TOC entry 4906 (class 0 OID 16389)
-- Dependencies: 217
-- Data for Name: material; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.material (materialcode, materialname, materialdescription) FROM stdin;
1	Iron Ore	Raw iron ore for processing
\.


--
-- TOC entry 4908 (class 0 OID 16393)
-- Dependencies: 219
-- Data for Name: shiftmaster; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.shiftmaster (shiftname, fromshift, toshift) FROM stdin;
Morning	06:00:00	14:00:00
\.


--
-- TOC entry 4909 (class 0 OID 16396)
-- Dependencies: 220
-- Data for Name: suppliers; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.suppliers (suppliercode, suppliername, supplieraddress, contactperson, contactnumber) FROM stdin;
1	ABC Metals	123 Industrial Area	Mr. Kumar	9000000001
\.


--
-- TOC entry 4917 (class 0 OID 16450)
-- Dependencies: 228
-- Data for Name: templatefields; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.templatefields (templatename, fieldname, displayname, x, y, width, height, fontname, fontsize) FROM stdin;
TEST22	TicketNumber	TicketNumber	10	10	50	10	Tahoma	10
TEST22	VehicleNumber	VehicleNumber	10	0	50	10	Tahoma	10
TEST2	TicketNumber	TicketNumber	10	10	50	10	Tahoma	10
TEST2	VehicleNumber	VehicleNumber	10	0	50	10	Tahoma	10
TEST2	Date	Date	10	20	50	10	Tahoma	10
\.


--
-- TOC entry 4916 (class 0 OID 16443)
-- Dependencies: 227
-- Data for Name: templatemaster; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.templatemaster (templatename, ticketheight, ticketwidth, defaulttemplate) FROM stdin;
TEST22	100	150	f
TEST2	100	150	f
\.


--
-- TOC entry 4911 (class 0 OID 16400)
-- Dependencies: 222
-- Data for Name: tickets; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tickets ("TicketNumber", "VehicleNumber", "Date", "Time", "EmptyWeight", "LoadedWeight", "EmptyWeightDate", "EmptyWeightTime", "LoadWeightDate", "LoadWeightTime", "NetWeight", "Pending", "Closed", "Exported", "Shift", "Materialname", "SupplierName", "State", "Blank", "AMOUNT", "STATUS", "EAMOUNT", "LAMOUNT", "TAMOUNT", "NetWeight1", "LWEIGHT", "EWEIGHT") FROM stdin;
15045	TN20BP0505	2025-06-24	11:41:07.055	1000	6805	2025-06-24	11:41:07.055	2025-06-24	11:41:07.055	5805	f	t	f	B				\N	\N		\N	100	\N	\N	\N	\N
15046	TN21F3637	2025-06-24	11:47:31.415	6597	20225	2025-06-24	11:47:31.415	2025-06-24	11:47:31.415	13628	f	t	f	B				\N	\N		\N	\N	\N	\N	\N	\N
19522	TN20Q0505	2025-06-24	22:55:41	3000	30684	2025-06-24	22:55:41	2025-06-24	22:55:41	27684	f	t	f	B				\N	\N		\N	180	\N	\N	\N	\N
19523	TN20Q0505	2025-06-25	02:10:43	3000	23581	2025-06-25	02:10:43	2025-06-25	02:10:43	20581	f	t	f	B				\N	\N		\N	200	\N	\N	\N	\N
19521	TMK55	2025-06-25	16:34:18	34297	39209	2025-06-25	16:34:18	2025-06-25	16:34:18	4912	f	t	f	B				\N	\N		100	200	\N	\N	\N	\N
17629	TN21Z2030	2025-06-25	17:05:07	\N	20000	2025-06-25	17:05:07	2025-06-25	17:05:07	\N	f	f	f	B				\N	\N		\N	\N	\N	\N	\N	\N
19524	TN20BB6145	2025-06-25	21:50:14	31659	48688	2025-06-25	21:50:14	2025-06-25	21:50:14	17029	f	t	f	B				\N	\N		\N	\N	\N	\N	\N	\N
19525	TN20X7575	2025-06-25	21:54:34	28677	15378	2025-06-25	21:54:34	2025-06-25	21:54:34	-13299	f	t	f	B				\N	\N		\N	250	\N	\N	\N	\N
19526	TN20X7575	2025-06-25	22:00:13	18336	39170	2025-06-25	22:00:13	2025-06-25	22:00:13	20834	f	t	f	B				\N	\N		\N	\N	\N	\N	\N	\N
19527	TN23F3637	2025-06-25	22:04:45	\N	29034	2025-06-25	22:04:45	2025-06-25	22:04:45	29034	t	f	f	B				\N	\N		\N	\N	\N	\N	\N	\N
15044	TSR1904	2025-06-25	22:16:16	34573	30429	2025-06-25	22:16:16	2025-06-25	22:16:16	-4144	f	t	f	B				\N	\N		100	200	\N	\N	\N	\N
19528	TN20Q0505	2025-06-25	22:17:09	3000	11357	2025-06-25	22:17:09	2025-06-25	22:17:09	8357	f	t	f	B				\N	\N		\N	100	\N	\N	\N	\N
19529	TN20X8080	2025-06-25	22:33:45	15638	19882	2025-06-25	22:33:45	2025-06-25	22:33:45	4244	f	t	f	B				\N	\N		100	\N	\N	\N	\N	\N
19530	TN12X45454	2025-06-25	22:55:38	37374	18505	2025-06-25	22:55:38	2025-06-25	22:55:38	-18869	f	t	f	B				\N	\N		100	\N	\N	\N	\N	\N
19531	TN20Q0505	2025-06-25	22:56:11	3000	37616	2025-06-25	22:56:11	2025-06-25	22:56:11	34616	f	t	f	B				\N	\N		\N	\N	\N	\N	\N	\N
19533	TN12CX0505	2025-06-26	13:10:38	45991	\N	\N	\N	\N	\N	45991	f	\N	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19535	TN20K0606	2025-06-26	18:39:27	\N	49007	\N	\N	2025-06-26	18:39:27	\N	f	t	\N	\N	\N	\N	\N	\N	\N	\N	\N	60	60	\N	\N	\N
19538	TN20BY7654	2025-06-26	22:18:40	9764	21673	2025-06-26	22:18:40	2025-06-26	22:18:40	11909	f	t	f	B				\N	\N		\N	200	\N	\N	\N	\N
19537	TN12E9555	2025-06-26	21:40:26	\N	24882	\N	\N	\N	\N	24882	f	\N	\N	\N	\N	\N	\N	\N	\N	\N	\N	60	60	\N	\N	\N
19539	TN12AZ1234	2025-06-27	00:12:26	\N	25228	\N	\N	\N	\N	25228	f	t	\N	\N	\N	\N	\N	\N	\N	\N	\N	60	60	\N	\N	\N
19536	TN20AS5979	2025-06-26	19:44:24	\N	36755	\N	\N	2025-06-26	19:44:24	\N	f	t	\N	\N	\N	\N	\N	\N	\N	\N	\N	80	80	\N	\N	\N
19540	TN20XX6969	2025-06-27	01:17:03	\N	40891	2025-06-27	01:17:03	2025-06-27	01:17:03	\N	f	t	f	B				\N	\N		\N	\N	\N	\N	\N	\N
19541	TN70M0060	2025-06-27	01:49:57	6639	37414	\N	\N	2025-06-27	01:49:57	30775	f	t	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19542	TN12ZX7474	2025-06-29	13:59:31	24381	\N	\N	\N	\N	\N	24381	f	t	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19534	TN20CX0505	2025-06-26	17:13:15	51663	18782	\N	\N	2025-06-26	17:13:15	32881	f	t	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19543	TN20Q0505	2025-06-29	16:30:18	3000	23777	2025-06-29	16:30:18	2025-06-29	16:30:18	20777	f	t	f	B				\N	\N		\N	\N	\N	\N	\N	\N
19544	TN20DB2341	2025-06-29	16:31:50	42099	45625	2025-06-29	16:31:50	2025-06-29	16:31:50	3526	f	t	f	B				\N	\N	EMPTY	100	\N	\N	\N	\N	\N
19545	TN70NR2505	2025-06-29	16:44:59	14281	\N	2025-06-29	16:44:59	2025-06-29	16:44:59	14281	t	f	f	B				\N	\N	EMPTY	\N	\N	\N	\N	\N	\N
19519	TN12Z2030	2025-06-29	16:45:42	\N	20000	2025-06-29	16:45:42	2025-06-29	16:45:42	\N	f	f	f	B				\N	\N		\N	\N	\N	\N	\N	\N
19532	TN12B4545	2025-06-25	23:00:12	45656	26980	2025-06-25	23:00:12	2025-06-25	23:00:12	-18676	f	t	f	B				\N	\N		\N	\N	\N	\N	\N	\N
19546	TMK0505	2025-06-29	20:48:39	8745	\N	\N	\N	\N	\N	8745	f	t	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19547	TN05ZX0505	2025-06-29	21:19:01	12403	\N	\N	\N	\N	\N	12403	f	t	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19548	TN02F3456	2025-06-29	21:23:31	6765	\N	\N	\N	\N	\N	6765	f	t	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19549	TN20Q0505	2025-06-29	23:03:57	20206	32607	2025-06-29	23:03:57	2025-06-29	23:03:57	12401	f	t	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19550	TN20XX3399	2025-06-29	23:21:16	33933	\N	\N	\N	\N	\N	33933	f	f	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19551	TN20RS1432	2025-06-29	23:26:20	28239	\N	\N	\N	\N	\N	28239	t	f	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19552	TN13Y6780	2025-06-29	23:29:50	16492	9000	2025-06-29	23:29:50	2025-06-29	23:29:50	-7492	f	t	\N	\N	\N	\N	\N	\N	\N	\N	\N	60	60	\N	\N	\N
19553	TN45EF0505	2025-06-30	00:00:28	5699	\N	\N	\N	\N	\N	5699	t	f	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19555	TN12EX0505	2025-06-30	14:15:23	6916	27575	2025-06-30	14:15:23	2025-06-30	14:15:23	20659	f	t	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19554	TN12EX8901	2025-06-30	13:50:44	7345	41533	2025-06-30	13:50:44	2025-06-30	13:50:44	34188	f	t	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19556	TN12AS5979	2025-06-30	23:51:42	7988	\N	\N	\N	\N	\N	7988	t	f	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19557	TN12X4545	2025-07-01	11:19:23	11116	31003	2025-07-01	11:19:23	2025-07-01	11:19:23	19887	f	t	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19558	TN12TU3456	2025-07-01	11:48:37	12180	26874	2025-07-01	11:48:37	2025-07-01	11:48:37	14694	f	t	f	B				\N	\N	LOAD	\N	\N	\N	\N	\N	\N
\.


--
-- TOC entry 4912 (class 0 OID 16405)
-- Dependencies: 223
-- Data for Name: usermanagement; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.usermanagement (userid, username, password, retypepasswd, offlinetickets, deleterecords, duplicateticket, vehiclemaster, adminuser, primaryuser) FROM stdin;
1	admin	adminpass	adminpass	f	f	f	f	t	t
2	ADMIN	ADMIN	\N	f	f	f	f	f	f
\.


--
-- TOC entry 4914 (class 0 OID 16415)
-- Dependencies: 225
-- Data for Name: vehiclemaster; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.vehiclemaster (vehicleid, vehiclenumber, vehicletareweight) FROM stdin;
1	TN20BP0505	1000
2	TN21Z2030	9000
3	TN20Q0505	3000
\.


--
-- TOC entry 4927 (class 0 OID 0)
-- Dependencies: 218
-- Name: material_materialcode_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.material_materialcode_seq', 1, true);


--
-- TOC entry 4928 (class 0 OID 0)
-- Dependencies: 221
-- Name: suppliers_suppliercode_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.suppliers_suppliercode_seq', 1, true);


--
-- TOC entry 4929 (class 0 OID 0)
-- Dependencies: 224
-- Name: usermanagement_userid_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.usermanagement_userid_seq', 2, true);


--
-- TOC entry 4930 (class 0 OID 0)
-- Dependencies: 226
-- Name: vehiclemaster_vehicleid_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.vehiclemaster_vehicleid_seq', 1, true);


--
-- TOC entry 4737 (class 2606 OID 16424)
-- Name: material material_materialname_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material
    ADD CONSTRAINT material_materialname_key UNIQUE (materialname);


--
-- TOC entry 4739 (class 2606 OID 16426)
-- Name: material material_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material
    ADD CONSTRAINT material_pkey PRIMARY KEY (materialcode);


--
-- TOC entry 4741 (class 2606 OID 16428)
-- Name: shiftmaster shiftmaster_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shiftmaster
    ADD CONSTRAINT shiftmaster_pkey PRIMARY KEY (shiftname);


--
-- TOC entry 4743 (class 2606 OID 16430)
-- Name: suppliers suppliers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.suppliers
    ADD CONSTRAINT suppliers_pkey PRIMARY KEY (suppliercode);


--
-- TOC entry 4745 (class 2606 OID 16432)
-- Name: suppliers suppliers_suppliername_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.suppliers
    ADD CONSTRAINT suppliers_suppliername_key UNIQUE (suppliername);


--
-- TOC entry 4759 (class 2606 OID 16456)
-- Name: templatefields templatefields_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.templatefields
    ADD CONSTRAINT templatefields_pkey PRIMARY KEY (templatename, fieldname);


--
-- TOC entry 4757 (class 2606 OID 16449)
-- Name: templatemaster templatemaster_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.templatemaster
    ADD CONSTRAINT templatemaster_pkey PRIMARY KEY (templatename);


--
-- TOC entry 4747 (class 2606 OID 16434)
-- Name: tickets tickets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tickets
    ADD CONSTRAINT tickets_pkey PRIMARY KEY ("TicketNumber");


--
-- TOC entry 4749 (class 2606 OID 16436)
-- Name: usermanagement usermanagement_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usermanagement
    ADD CONSTRAINT usermanagement_pkey PRIMARY KEY (userid);


--
-- TOC entry 4751 (class 2606 OID 16438)
-- Name: usermanagement usermanagement_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usermanagement
    ADD CONSTRAINT usermanagement_username_key UNIQUE (username);


--
-- TOC entry 4753 (class 2606 OID 16440)
-- Name: vehiclemaster vehiclemaster_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehiclemaster
    ADD CONSTRAINT vehiclemaster_pkey PRIMARY KEY (vehicleid);


--
-- TOC entry 4755 (class 2606 OID 16442)
-- Name: vehiclemaster vehiclemaster_vehiclenumber_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehiclemaster
    ADD CONSTRAINT vehiclemaster_vehiclenumber_key UNIQUE (vehiclenumber);


--
-- TOC entry 4760 (class 2606 OID 16457)
-- Name: templatefields templatefields_templatename_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.templatefields
    ADD CONSTRAINT templatefields_templatename_fkey FOREIGN KEY (templatename) REFERENCES public.templatemaster(templatename);


-- Completed on 2025-07-02 15:25:55

--
-- PostgreSQL database dump complete
--

