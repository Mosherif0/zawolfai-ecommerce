--
-- PostgreSQL database dump
--

\restrict OP4A7CvdgxvcNOVDElZorAS3REv8laGPSSBQkKqmUcXTbI8g2Sf2kvYvT4N56kq

-- Dumped from database version 18.4
-- Dumped by pg_dump version 18.4

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

--
-- Name: public; Type: SCHEMA; Schema: -; Owner: -
--

CREATE SCHEMA public;


--
-- Name: SCHEMA public; Type: COMMENT; Schema: -; Owner: -
--

COMMENT ON SCHEMA public IS 'standard public schema';


SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: products; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.products (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    price numeric(10,2),
    quantity integer DEFAULT 0 NOT NULL,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP,
    updated_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: products_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.products_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: products_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.products_id_seq OWNED BY public.products.id;


--
-- Name: receipt_items; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.receipt_items (
    id integer NOT NULL,
    receipt_id integer NOT NULL,
    product_id integer NOT NULL,
    quantity integer NOT NULL,
    price numeric(10,2)
);


--
-- Name: receipt_items_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.receipt_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: receipt_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.receipt_items_id_seq OWNED BY public.receipt_items.id;


--
-- Name: receipts; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.receipts (
    id integer NOT NULL,
    receipt_date date,
    created_at timestamp without time zone DEFAULT CURRENT_TIMESTAMP
);


--
-- Name: receipts_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.receipts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: receipts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.receipts_id_seq OWNED BY public.receipts.id;


--
-- Name: products id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products ALTER COLUMN id SET DEFAULT nextval('public.products_id_seq'::regclass);


--
-- Name: receipt_items id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.receipt_items ALTER COLUMN id SET DEFAULT nextval('public.receipt_items_id_seq'::regclass);


--
-- Name: receipts id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.receipts ALTER COLUMN id SET DEFAULT nextval('public.receipts_id_seq'::regclass);


--
-- Data for Name: products; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.products (id, name, price, quantity, created_at, updated_at) FROM stdin;
2	Denim Jeans	49.99	1	2026-10-02 02:56:11.530735	2026-10-02 02:56:11.530735
6	Wide Leg Jean	69.99	4	2026-10-02 03:36:37.534437	2026-10-03 23:43:53.142855
14	Storage Box	199.00	1	2026-10-04 18:43:38.041243	2026-10-04 18:43:38.041243
1	Cotton T-Shirt	39.98	2	2026-10-02 02:56:11.530735	2026-10-04 18:47:47.376107
15	Denim Jean	49.99	1	2026-10-04 18:47:47.376107	2026-10-04 18:47:47.376107
16	White Sneaker	79.99	1	2026-10-04 18:47:47.376107	2026-10-04 18:47:47.376107
4	Black Blazer	59.99	5	2026-10-02 03:36:37.534437	2026-10-05 20:41:49
5	White Shirt	45.95	5	2026-10-02 03:36:37.534437	2026-10-05 20:41:49
19	Wide Leg Jeans	69.99	1	2026-10-05 20:41:49	2026-10-05 20:41:49
7	Leather Belt	25.00	5	2026-10-02 03:36:37.534437	2026-10-05 20:41:49
20	Panadol Tabs	45.00	1	2026-10-05 20:43:47	2026-10-05 20:43:47
21	Vitamin D3 Tabs	120.00	1	2026-10-05 20:43:47	2026-10-05 20:43:47
22	Skin Care Cream	85.00	1	2026-10-05 20:43:47	2026-10-05 20:43:47
23	Hand Sanitizer	30.00	1	2026-10-05 20:43:47	2026-10-05 20:43:47
8	Women Sweater	79.99	2	2026-10-04 18:38:57.809876	2026-10-07 23:42:40
9	Men Hoodie	99.99	2	2026-10-04 18:38:57.809876	2026-10-07 23:42:40
10	Kids T-Shirt	59.99	2	2026-10-04 18:38:57.809876	2026-10-07 23:42:40
17	KALLAX Shelf Unit	2495.00	5	2026-10-05 18:53:16	2026-10-07 23:54:40
12	Desk Lamp	599.00	6	2026-10-04 18:43:38.041243	2026-10-07 23:54:40
13	Plant Pot	149.00	6	2026-10-04 18:43:38.041243	2026-10-07 23:54:40
18	Storage Bo	199.00	5	2026-10-05 18:53:16	2026-10-07 23:54:40
\.


--
-- Data for Name: receipt_items; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.receipt_items (id, receipt_id, product_id, quantity, price) FROM stdin;
1	1	17	1	2495.00
2	1	12	1	599.00
3	1	13	1	149.00
4	1	18	1	199.00
5	2	17	1	2495.00
6	2	12	1	599.00
7	2	13	1	149.00
8	2	18	1	199.00
9	3	4	1	59.99
10	3	5	1	45.95
11	3	19	1	69.99
12	3	7	1	25.00
13	4	20	1	45.00
14	4	21	1	120.00
15	4	22	1	85.00
16	4	23	1	30.00
17	5	8	1	79.99
18	5	9	1	99.99
19	5	10	1	59.99
20	6	17	1	2495.00
21	6	12	1	599.00
22	6	13	1	149.00
23	6	18	1	199.00
24	7	17	1	2495.00
25	7	12	1	599.00
26	7	13	1	149.00
27	7	18	1	199.00
28	8	17	1	2495.00
29	8	12	1	599.00
30	8	13	1	149.00
31	8	18	1	199.00
\.


--
-- Data for Name: receipts; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.receipts (id, receipt_date, created_at) FROM stdin;
1	2026-10-05	2026-10-05 18:53:16
2	2026-10-05	2026-10-05 20:38:33
3	2026-10-05	2026-10-05 20:41:49
4	2026-10-05	2026-10-05 20:43:47
5	2026-10-07	2026-10-07 23:42:40
6	2026-10-07	2026-10-07 23:45:23
7	2026-10-07	2026-10-07 23:51:33
8	2026-10-07	2026-10-07 23:54:40
\.


--
-- Name: products_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.products_id_seq', 23, true);


--
-- Name: receipt_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.receipt_items_id_seq', 31, true);


--
-- Name: receipts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.receipts_id_seq', 8, true);


--
-- Name: products products_name_key; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_name_key UNIQUE (name);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: receipt_items receipt_items_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.receipt_items
    ADD CONSTRAINT receipt_items_pkey PRIMARY KEY (id);


--
-- Name: receipts receipts_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.receipts
    ADD CONSTRAINT receipts_pkey PRIMARY KEY (id);


--
-- Name: idx_items_product; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_items_product ON public.receipt_items USING btree (product_id);


--
-- Name: idx_items_receipt; Type: INDEX; Schema: public; Owner: -
--

CREATE INDEX idx_items_receipt ON public.receipt_items USING btree (receipt_id);


--
-- Name: receipt_items receipt_items_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.receipt_items
    ADD CONSTRAINT receipt_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: receipt_items receipt_items_receipt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.receipt_items
    ADD CONSTRAINT receipt_items_receipt_id_fkey FOREIGN KEY (receipt_id) REFERENCES public.receipts(id);


--
-- PostgreSQL database dump complete
--

\unrestrict OP4A7CvdgxvcNOVDElZorAS3REv8laGPSSBQkKqmUcXTbI8g2Sf2kvYvT4N56kq

