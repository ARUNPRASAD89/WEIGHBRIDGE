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
19559	TN12XP0505	2025-07-02	23:26:00	9968	\N	\N	\N	\N	\N	9968	t	f	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19560	TN12EB7575	2025-07-03	15:13:08	8326	\N	\N	\N	\N	\N	8326	t	f	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19561	TN12NM7755	2025-07-03	15:21:10	5267	\N	\N	\N	\N	\N	5267	t	f	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19562	TN12AP5656	2025-07-03	15:28:41	7641	\N	\N	\N	\N	\N	7641	t	f	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19563	TN12XY1234	2025-07-03	16:54:29	10021	\N	\N	\N	\N	\N	10021	t	f	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19564	TN12XY7890	2025-07-03	16:56:30	10919	\N	\N	\N	\N	\N	10919	t	f	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19565	TN45XY1234	2025-07-03	17:26:25	10435	\N	\N	\N	\N	\N	10435	t	f	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19566	TN12XY4567	2025-07-03	17:46:41	10453	\N	\N	\N	\N	\N	10453	t	f	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19567	TN77IJ1111	2025-07-03	18:14:58	10560	\N	\N	\N	\N	\N	10560	t	f	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19568	TN12Y1456	2025-07-03	18:35:56	7270	\N	\N	\N	\N	\N	7270	t	f	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19569	TN12FG3456	2025-07-03	20:06:11	11436	\N	\N	\N	\N	\N	11436	t	f	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
19570	TN12M2050	2025-07-03	21:43:34	11402	\N	\N	\N	\N	\N	11402	t	f	\N	\N	\N	\N	\N	\N	\N	\N	60	\N	60	\N	\N	\N
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

