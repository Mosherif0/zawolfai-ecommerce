--
-- PostgreSQL database dump
--

\restrict ezuSVjKWTs09ZfYvJDpIZX2OjGHNFNOos74DqiPgmbG95tPVAGc3uRryeONvopW

-- Dumped from database version 18.6
-- Dumped by pg_dump version 18.6

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
-- Name: categories; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.categories (
    id integer NOT NULL,
    name text NOT NULL
);


ALTER TABLE public.categories OWNER TO postgres;

--
-- Name: categories_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.categories_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.categories_id_seq OWNER TO postgres;

--
-- Name: categories_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.categories_id_seq OWNED BY public.categories.id;


--
-- Name: products; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.products (
    id integer NOT NULL,
    name text NOT NULL,
    price double precision DEFAULT 0 NOT NULL,
    quantity integer DEFAULT 0 NOT NULL,
    category_id integer,
    supplier_id integer,
    barcode text,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.products OWNER TO postgres;

--
-- Name: products_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.products_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.products_id_seq OWNER TO postgres;

--
-- Name: products_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.products_id_seq OWNED BY public.products.id;


--
-- Name: receipt_items; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.receipt_items (
    id integer NOT NULL,
    receipt_id integer,
    product_id integer,
    name_raw text NOT NULL,
    quantity integer DEFAULT 1 NOT NULL,
    unit_price double precision NOT NULL,
    line_total double precision,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.receipt_items OWNER TO postgres;

--
-- Name: receipt_items_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.receipt_items_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.receipt_items_id_seq OWNER TO postgres;

--
-- Name: receipt_items_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.receipt_items_id_seq OWNED BY public.receipt_items.id;


--
-- Name: receipts; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.receipts (
    id integer NOT NULL,
    source_file text,
    store text,
    receipt_date text,
    total double precision,
    language text,
    status text DEFAULT 'accepted'::text NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.receipts OWNER TO postgres;

--
-- Name: receipts_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.receipts_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.receipts_id_seq OWNER TO postgres;

--
-- Name: receipts_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.receipts_id_seq OWNED BY public.receipts.id;


--
-- Name: stock_movements; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.stock_movements (
    id integer NOT NULL,
    product_id integer NOT NULL,
    delta integer NOT NULL,
    reason text NOT NULL,
    ref_type text,
    ref_id integer,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.stock_movements OWNER TO postgres;

--
-- Name: stock_movements_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.stock_movements_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.stock_movements_id_seq OWNER TO postgres;

--
-- Name: stock_movements_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.stock_movements_id_seq OWNED BY public.stock_movements.id;


--
-- Name: suppliers; Type: TABLE; Schema: public; Owner: postgres
--

CREATE TABLE public.suppliers (
    id integer NOT NULL,
    name text NOT NULL,
    created_at timestamp with time zone DEFAULT CURRENT_TIMESTAMP NOT NULL
);


ALTER TABLE public.suppliers OWNER TO postgres;

--
-- Name: suppliers_id_seq; Type: SEQUENCE; Schema: public; Owner: postgres
--

CREATE SEQUENCE public.suppliers_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER SEQUENCE public.suppliers_id_seq OWNER TO postgres;

--
-- Name: suppliers_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: postgres
--

ALTER SEQUENCE public.suppliers_id_seq OWNED BY public.suppliers.id;


--
-- Name: categories id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.categories ALTER COLUMN id SET DEFAULT nextval('public.categories_id_seq'::regclass);


--
-- Name: products id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products ALTER COLUMN id SET DEFAULT nextval('public.products_id_seq'::regclass);


--
-- Name: receipt_items id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.receipt_items ALTER COLUMN id SET DEFAULT nextval('public.receipt_items_id_seq'::regclass);


--
-- Name: receipts id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.receipts ALTER COLUMN id SET DEFAULT nextval('public.receipts_id_seq'::regclass);


--
-- Name: stock_movements id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_movements ALTER COLUMN id SET DEFAULT nextval('public.stock_movements_id_seq'::regclass);


--
-- Name: suppliers id; Type: DEFAULT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.suppliers ALTER COLUMN id SET DEFAULT nextval('public.suppliers_id_seq'::regclass);


--
-- Data for Name: categories; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.categories (id, name) FROM stdin;
\.


--
-- Data for Name: products; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.products (id, name, price, quantity, category_id, supplier_id, barcode, created_at, updated_at) FROM stdin;
1	Black Blazer	59.99	1	\N	1	\N	2026-10-04 22:01:58+03	2026-10-04 22:01:58+03
3	Wide Leg Jeans	69.99	1	\N	1	\N	2026-10-04 22:01:58+03	2026-10-04 22:01:58+03
4	Leather Belt	25	1	\N	1	\N	2026-10-04 22:01:58+03	2026-10-04 22:01:58+03
2	White Shirt	45.95	0	\N	1	\N	2026-10-04 22:01:58+03	2026-10-04 22:04:48+03
\.


--
-- Data for Name: receipt_items; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.receipt_items (id, receipt_id, product_id, name_raw, quantity, unit_price, line_total, created_at) FROM stdin;
1	1	1	Black Blazer	1	59.99	59.99	2026-10-04 22:01:58+03
2	1	2	White Shirt	1	45.95	45.95	2026-10-04 22:01:58+03
3	1	3	Wide Leg Jeans	1	69.99	69.99	2026-10-04 22:01:58+03
4	1	4	Leather Belt	1	25	25	2026-10-04 22:01:58+03
\.


--
-- Data for Name: receipts; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.receipts (id, source_file, store, receipt_date, total, language, status, created_at) FROM stdin;
1	ZARA_6.22.44PM.jpg	ZARA Egypt	\N	200.93	en	accepted	2026-10-04 22:01:58+03
\.


--
-- Data for Name: stock_movements; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.stock_movements (id, product_id, delta, reason, ref_type, ref_id, created_at) FROM stdin;
1	1	1	receipt_scan	receipt	1	2026-10-04 22:01:58+03
2	2	1	receipt_scan	receipt	1	2026-10-04 22:01:58+03
3	3	1	receipt_scan	receipt	1	2026-10-04 22:01:58+03
4	4	1	receipt_scan	receipt	1	2026-10-04 22:01:58+03
5	2	-1	sale	manual	\N	2026-10-04 22:04:48+03
\.


--
-- Data for Name: suppliers; Type: TABLE DATA; Schema: public; Owner: postgres
--

COPY public.suppliers (id, name, created_at) FROM stdin;
1	ZARA Egypt	2026-10-04 22:01:58+03
\.


--
-- Name: categories_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.categories_id_seq', 1, false);


--
-- Name: products_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.products_id_seq', 4, true);


--
-- Name: receipt_items_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.receipt_items_id_seq', 4, true);


--
-- Name: receipts_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.receipts_id_seq', 1, true);


--
-- Name: stock_movements_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.stock_movements_id_seq', 5, true);


--
-- Name: suppliers_id_seq; Type: SEQUENCE SET; Schema: public; Owner: postgres
--

SELECT pg_catalog.setval('public.suppliers_id_seq', 1, true);


--
-- Name: categories categories_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_name_key UNIQUE (name);


--
-- Name: categories categories_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.categories
    ADD CONSTRAINT categories_pkey PRIMARY KEY (id);


--
-- Name: products products_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_name_key UNIQUE (name);


--
-- Name: products products_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_pkey PRIMARY KEY (id);


--
-- Name: receipt_items receipt_items_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.receipt_items
    ADD CONSTRAINT receipt_items_pkey PRIMARY KEY (id);


--
-- Name: receipts receipts_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.receipts
    ADD CONSTRAINT receipts_pkey PRIMARY KEY (id);


--
-- Name: stock_movements stock_movements_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_movements
    ADD CONSTRAINT stock_movements_pkey PRIMARY KEY (id);


--
-- Name: suppliers suppliers_name_key; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.suppliers
    ADD CONSTRAINT suppliers_name_key UNIQUE (name);


--
-- Name: suppliers suppliers_pkey; Type: CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.suppliers
    ADD CONSTRAINT suppliers_pkey PRIMARY KEY (id);


--
-- Name: idx_items_product; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_items_product ON public.receipt_items USING btree (product_id);


--
-- Name: idx_items_receipt; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_items_receipt ON public.receipt_items USING btree (receipt_id);


--
-- Name: idx_moves_product; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_moves_product ON public.stock_movements USING btree (product_id);


--
-- Name: idx_products_cat; Type: INDEX; Schema: public; Owner: postgres
--

CREATE INDEX idx_products_cat ON public.products USING btree (category_id);


--
-- Name: products products_category_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_category_id_fkey FOREIGN KEY (category_id) REFERENCES public.categories(id);


--
-- Name: products products_supplier_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.products
    ADD CONSTRAINT products_supplier_id_fkey FOREIGN KEY (supplier_id) REFERENCES public.suppliers(id);


--
-- Name: receipt_items receipt_items_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.receipt_items
    ADD CONSTRAINT receipt_items_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id);


--
-- Name: receipt_items receipt_items_receipt_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.receipt_items
    ADD CONSTRAINT receipt_items_receipt_id_fkey FOREIGN KEY (receipt_id) REFERENCES public.receipts(id) ON DELETE CASCADE;


--
-- Name: stock_movements stock_movements_product_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: postgres
--

ALTER TABLE ONLY public.stock_movements
    ADD CONSTRAINT stock_movements_product_id_fkey FOREIGN KEY (product_id) REFERENCES public.products(id) ON DELETE CASCADE;


--
-- PostgreSQL database dump complete
--

\unrestrict ezuSVjKWTs09ZfYvJDpIZX2OjGHNFNOos74DqiPgmbG95tPVAGc3uRryeONvopW

