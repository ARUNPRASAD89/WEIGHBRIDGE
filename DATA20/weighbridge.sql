--
-- PostgreSQL database dump
--

-- Dumped from database version 17.5
-- Dumped by pg_dump version 17.5

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
-- Name: material; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.material (
    materialcode integer NOT NULL,
    materialname character varying(100) NOT NULL,
    materialdescription character varying(255)
);


ALTER TABLE public.material OWNER TO postgres;

--
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
-- Name: material_materialcode_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.material_materialcode_seq OWNED BY public.material.materialcode;


--
-- Name: shiftmaster; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.shiftmaster (
    shiftname character varying(50) NOT NULL,
    fromshift time without time zone,
    toshift time without time zone
);


ALTER TABLE public.shiftmaster OWNER TO postgres;

--
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
-- Name: suppliers_suppliercode_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.suppliers_suppliercode_seq OWNED BY public.suppliers.suppliercode;


--
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
    fontsize integer,
    id integer NOT NULL
);


ALTER TABLE public.templatefields OWNER TO postgres;

--
-- Name: templatefields_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.templatefields_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.templatefields_id_seq OWNER TO postgres;

--
-- Name: templatefields_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.templatefields_id_seq OWNED BY public.templatefields.id;


--
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
-- Name: usermanagement_userid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.usermanagement_userid_seq OWNED BY public.usermanagement.userid;


--
-- Name: vehiclemaster; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.vehiclemaster (
    vehicleid integer NOT NULL,
    vehiclenumber character varying(50) NOT NULL,
    vehicletareweight integer
);


ALTER TABLE public.vehiclemaster OWNER TO postgres;

--
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
-- Name: vehiclemaster_vehicleid_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.vehiclemaster_vehicleid_seq OWNED BY public.vehiclemaster.vehicleid;


--
-- Name: material materialcode; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material ALTER COLUMN materialcode SET DEFAULT nextval('public.material_materialcode_seq'::regclass);


--
-- Name: suppliers suppliercode; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.suppliers ALTER COLUMN suppliercode SET DEFAULT nextval('public.suppliers_suppliercode_seq'::regclass);


--
-- Name: templatefields id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.templatefields ALTER COLUMN id SET DEFAULT nextval('public.templatefields_id_seq'::regclass);


--
-- Name: usermanagement userid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usermanagement ALTER COLUMN userid SET DEFAULT nextval('public.usermanagement_userid_seq'::regclass);


--
-- Name: vehiclemaster vehicleid; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehiclemaster ALTER COLUMN vehicleid SET DEFAULT nextval('public.vehiclemaster_vehicleid_seq'::regclass);


--
-- Data for Name: material; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.material (materialcode, materialname, materialdescription) FROM stdin;
1	Iron Ore	Raw iron ore for processing
\.


--
-- Data for Name: shiftmaster; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.shiftmaster (shiftname, fromshift, toshift) FROM stdin;
Morning	06:00:00	14:00:00
\.


--
-- Data for Name: suppliers; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.suppliers (suppliercode, suppliername, supplieraddress, contactperson, contactnumber) FROM stdin;
1	ABC Metals	123 Industrial Area	Mr. Kumar	9000000001
\.


--
-- Data for Name: templatefields; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.templatefields (templatename, fieldname, displayname, x, y, width, height, fontname, fontsize, id) FROM stdin;
TEST22	TicketNumber	TicketNumber	10	10	50	10	Tahoma	10	1
TEST22	VehicleNumber	VehicleNumber	10	0	50	10	Tahoma	10	2
TEST2	TicketNumber	TicketNumber	10	10	50	10	Tahoma	10	3
TEST2	VehicleNumber	VehicleNumber	10	0	50	10	Tahoma	10	4
TEST2	Date	Date	10	20	50	10	Tahoma	10	5
new	TicketNumber	TicketNumber	26	38	32	10	Tahoma	10	6
NEW1	TicketNumber	TicketNumber	26	38	32	10	Tahoma	10	7
NEW02	TicketNumber	TicketNumber	27	39	31	10	Tahoma	10	8
NEW03	TicketNumber	TicketNumber	28	37	50	9	Tahoma	10	9
NEW04	TicketNumber	TicketNumber	33	39	50	10	Tahoma	10	10
RAVEN	TicketNumber	TicketNumber	26	39	33	10	Tahoma	10	155
RAVEN	Time	Time	102	43	18	7	Tahoma	10	157
RAVEN	EAMOUNT	EAMOUNT	34	64	24	7	Tahoma	10	159
RAVEN	TAMOUNT	TAMOUNT	92	64	24	7	Tahoma	10	161
RAVEN	SupplierName	SupplierName	200	71	31	7	Tahoma	10	163
RAVEN	LoadedWeight	LoadedWeight	160	81	31	7	Tahoma	10	165
RAVEN	NetWeight	NetWeight	35	99	31	7	Tahoma	10	167
RAVEN	TicketNumber	TicketNumber	152	38	33	10	Tahoma	10	169
RAVEN	Time	Time	229	43	18	7	Tahoma	10	171
RAVEN	EAMOUNT	EAMOUNT	160	64	24	7	Tahoma	10	173
RAVEN	TAMOUNT	TAMOUNT	220	64	24	7	Tahoma	10	175
RAVEN	LoadedWeight	LoadedWeight	35	81	31	7	Tahoma	10	177
RAVEN	NetWeight	NetWeight	159	99	31	7	Tahoma	10	179
RAVEN	State	State	37	117	31	7	Tahoma	10	181
RAVEN	Date	Date	229	37	18	8	Tahoma	10	156
RAVEN	VehicleNumber	VehicleNumber	33	54	36	7	Tahoma	10	158
RAVEN	LAMOUNT	LAMOUNT	188	64	24	7	Tahoma	10	160
RAVEN	Materialname	Materialname	34	72	31	7	Tahoma	10	162
RAVEN	SupplierName	SupplierName	70	72	31	7	Tahoma	10	164
RAVEN	EmptyWeight	EmptyWeight	34	90	31	7	Tahoma	10	166
RAVEN	STATUS	STATUS	37	108	31	7	Tahoma	10	168
RAVEN	Date	Date	102	37	18	7	Tahoma	10	170
RAVEN	VehicleNumber	VehicleNumber	159	54	36	7	Tahoma	10	172
RAVEN	LAMOUNT	LAMOUNT	64	64	24	7	Tahoma	10	174
RAVEN	Materialname	Materialname	159	71	31	7	Tahoma	10	176
RAVEN	EmptyWeight	EmptyWeight	159	90	31	7	Tahoma	10	178
RAVEN	STATUS	STATUS	166	108	31	7	Tahoma	10	180
\.


--
-- Data for Name: templatemaster; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.templatemaster (templatename, ticketheight, ticketwidth, defaulttemplate) FROM stdin;
TEST22	100	150	f
TEST2	100	150	f
new	153	254	f
NEW1	153	254	f
NEW02	153	254	f
NEW03	153	254	f
NEW04	154	254	f
RAVEN	154	254	t
\.


--
-- Data for Name: tickets; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.tickets ("TicketNumber", "VehicleNumber", "Date", "Time", "EmptyWeight", "LoadedWeight", "EmptyWeightDate", "EmptyWeightTime", "LoadWeightDate", "LoadWeightTime", "NetWeight", "Pending", "Closed", "Exported", "Shift", "Materialname", "SupplierName", "State", "Blank", "AMOUNT", "STATUS", "EAMOUNT", "LAMOUNT", "TAMOUNT", "NetWeight1", "LWEIGHT", "EWEIGHT") FROM stdin;
1	TN20AS5979	2025-07-06	23:47:51	6542	\N	\N	\N	\N	\N	6542	\N	\N	\N	\N			first transaction	\N	\N	Empty	60	\N	60	\N	\N	\N
2	TN12AL8933	2025-07-06	23:52:44	\N	39020	2025-07-06	23:52:44	2025-07-06	23:52:44	39020	t	f	f	B			first transaction	\N	\N	LOAD	\N	\N	\N	\N	\N	\N
4	TN77Q0505	2025-07-07	00:34:34	7235	\N	\N	\N	\N	\N	7235	\N	\N	\N	\N			first transaction	\N	\N	Empty	60	\N	60	\N	\N	\N
6	TN05RS5050	2025-07-07	20:01:09	11007	\N	2025-07-07	20:01:09	2025-07-07	20:01:09	11007	t	f	f	B			first transaction	\N	\N	Empty	60	\N	60	\N	\N	\N
7	TN77RS4545	2025-07-07	20:04:09	5438	\N	\N	\N	\N	\N	5438	\N	\N	\N	\N			first transaction	\N	\N	Empty	60	\N	60	\N	\N	\N
8	TN77MN0505	2025-07-07	20:13:52	10003	\N	2025-07-07	20:13:52	2025-07-07	20:13:52	10003	t	f	f	B			first transaction	\N	\N	Empty	60	\N	60	\N	\N	\N
9	TN05FG7894	2025-07-07	20:29:09	9912	\N	2025-07-07	20:29:09	2025-07-07	20:29:09	9912	t	f	f	B			first transaction	\N	\N	Empty	60	\N	60	\N	\N	\N
10	TN77F3456	2025-07-07	20:59:47	\N	17435	2025-07-07	20:59:47	2025-07-07	20:59:47	17435	t	f	f	B			first transaction	\N	\N	LOAD	\N	\N	\N	\N	\N	\N
11	MH04FG7894	2025-07-07	21:30:26	9385	\N	2025-07-07	21:30:26	2025-07-07	21:30:26	9385	t	f	f	B			first transaction	\N	\N	Empty	60	\N	60	\N	\N	\N
3	TN20BP0505	2025-07-07	22:44:48	23471	24006	2025-07-07	22:44:48	2025-07-07	22:44:48	535	f	t	f	B			second transaction	\N	\N	EMPTY	\N	\N	\N	\N	\N	\N
16	TN45RS7575	2025-07-07	22:57:08	10602	\N	2025-07-07	22:57:08	2025-07-07	22:57:08	10602	t	f	f	B			first transaction	\N	\N	Empty	60	\N	60	\N	\N	\N
20	TN70F1234	2025-07-07	23:37:03	\N	32644	2025-07-07	23:37:03	2025-07-07	23:37:03	32644	t	f	f	B			first transaction	\N	\N	LOAD	\N	\N	\N	\N	\N	\N
19	TN05JK7575	2025-07-07	23:36:19	11410	6319	2025-07-07	23:36:19	2025-07-07	23:36:19	-5091	f	t	f	B			second transaction	\N	\N		60	\N	60	\N	\N	\N
5	NL01LM7531	2025-07-07	00:41:03	5278	5290	2025-07-07	00:41:03	2025-07-07	00:41:03	12	f	t	f	B			second transaction	\N	\N		60	\N	60	\N	\N	\N
12	TN45ST7894	2025-07-07	21:47:32	9630	13617	2025-07-07	21:47:32	2025-07-07	21:47:32	3987	f	t	f	B			second transaction	\N	\N		60	\N	60	\N	\N	\N
14	TN05CD5050	2025-07-07	21:58:07	9425	6347	2025-07-07	21:58:07	2025-07-07	21:58:07	-3078	f	t	f	B			second transaction	\N	\N		60	\N	60	\N	\N	\N
13	TN07IJ0555	2025-07-07	21:49:33	11571	13558	2025-07-07	21:49:33	2025-07-07	21:49:33	1987	f	t	f	B			second transaction	\N	\N		60	\N	60	\N	\N	\N
15	TN77RS4141	2025-07-07	22:52:41	11650	13038	2025-07-07	22:52:41	2025-07-07	22:52:41	1388	f	t	f	B			second transaction	\N	\N		60	\N	60	\N	\N	\N
17	TN77XR1111	2025-07-07	23:10:37	10557	14871	2025-07-07	23:10:37	2025-07-07	23:10:37	4314	f	t	f	B			second transaction	\N	\N		60	\N	60	\N	\N	\N
18	TN12HP0505	2025-07-07	23:22:54	9496	10865	2025-07-07	23:22:54	2025-07-07	23:22:54	1369	f	t	f	B			second transaction	\N	\N		60	\N	60	\N	\N	\N
\.


--
-- Data for Name: usermanagement; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.usermanagement (userid, username, password, retypepasswd, offlinetickets, deleterecords, duplicateticket, vehiclemaster, adminuser, primaryuser) FROM stdin;
1	admin	adminpass	adminpass	f	f	f	f	t	t
2	ADMIN	ADMIN	\N	f	f	f	f	f	f
\.


--
-- Data for Name: vehiclemaster; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.vehiclemaster (vehicleid, vehiclenumber, vehicletareweight) FROM stdin;
1	TN20BP0505	1000
2	TN21Z2030	9000
3	TN20Q0505	3000
\.


--
-- Name: material_materialcode_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.material_materialcode_seq', 1, true);


--
-- Name: suppliers_suppliercode_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.suppliers_suppliercode_seq', 1, true);


--
-- Name: templatefields_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.templatefields_id_seq', 181, true);


--
-- Name: usermanagement_userid_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.usermanagement_userid_seq', 2, true);


--
-- Name: vehiclemaster_vehicleid_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.vehiclemaster_vehicleid_seq', 1, true);


--
-- Name: material material_materialname_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material
    ADD CONSTRAINT material_materialname_key UNIQUE (materialname);


--
-- Name: material material_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.material
    ADD CONSTRAINT material_pkey PRIMARY KEY (materialcode);


--
-- Name: shiftmaster shiftmaster_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.shiftmaster
    ADD CONSTRAINT shiftmaster_pkey PRIMARY KEY (shiftname);


--
-- Name: suppliers suppliers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.suppliers
    ADD CONSTRAINT suppliers_pkey PRIMARY KEY (suppliercode);


--
-- Name: suppliers suppliers_suppliername_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.suppliers
    ADD CONSTRAINT suppliers_suppliername_key UNIQUE (suppliername);


--
-- Name: templatefields templatefields_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.templatefields
    ADD CONSTRAINT templatefields_pkey PRIMARY KEY (id);


--
-- Name: templatemaster templatemaster_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.templatemaster
    ADD CONSTRAINT templatemaster_pkey PRIMARY KEY (templatename);


--
-- Name: tickets tickets_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.tickets
    ADD CONSTRAINT tickets_pkey PRIMARY KEY ("TicketNumber");


--
-- Name: usermanagement usermanagement_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usermanagement
    ADD CONSTRAINT usermanagement_pkey PRIMARY KEY (userid);


--
-- Name: usermanagement usermanagement_username_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.usermanagement
    ADD CONSTRAINT usermanagement_username_key UNIQUE (username);


--
-- Name: vehiclemaster vehiclemaster_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehiclemaster
    ADD CONSTRAINT vehiclemaster_pkey PRIMARY KEY (vehicleid);


--
-- Name: vehiclemaster vehiclemaster_vehiclenumber_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.vehiclemaster
    ADD CONSTRAINT vehiclemaster_vehiclenumber_key UNIQUE (vehiclenumber);


--
-- Name: templatefields templatefields_templatename_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.templatefields
    ADD CONSTRAINT templatefields_templatename_fkey FOREIGN KEY (templatename) REFERENCES public.templatemaster(templatename);


--
-- PostgreSQL database dump complete
--

