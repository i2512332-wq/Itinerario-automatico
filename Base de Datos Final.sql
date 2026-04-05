  -- 0. REINICIAR (Surgical cleanup compatible con Supabase)
  -- Borrar vistas si existen
  DROP VIEW IF EXISTS vista_servicios_diarios CASCADE;
  DROP VIEW IF EXISTS vista_ventas_completa CASCADE;

  -- Borrar tablas si existen (en orden de dependencia)
  DROP TABLE IF EXISTS pago_operativo CASCADE;
  DROP TABLE IF EXISTS venta_servicio_proveedor CASCADE;
  DROP TABLE IF EXISTS pasajero CASCADE;
  DROP TABLE IF EXISTS pago CASCADE;
  DROP TABLE IF EXISTS venta_item_ingreso CASCADE;
  DROP TABLE IF EXISTS venta_tour CASCADE;
  DROP TABLE IF EXISTS venta CASCADE;
  DROP TABLE IF EXISTS itinerario_digital CASCADE;
  DROP TABLE IF EXISTS paquete_personalizado CASCADE;
  DROP TABLE IF EXISTS paquete_tour CASCADE;
  DROP TABLE IF EXISTS paquete CASCADE;
  DROP TABLE IF EXISTS tour_itinerario_item CASCADE;
  DROP TABLE IF EXISTS tour CASCADE;
  DROP TABLE IF EXISTS plantilla_servicio CASCADE;
  DROP TABLE IF EXISTS proveedor CASCADE;
  DROP TABLE IF EXISTS agencia_aliada CASCADE;
  DROP TABLE IF EXISTS cliente CASCADE;
  DROP TABLE IF EXISTS lead CASCADE;
  DROP TABLE IF EXISTS vendedor CASCADE;
  DROP TABLE IF EXISTS usuarios_app CASCADE;

  -- Asegurar extensiones para UUIDs y Seguridad
  CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
  CREATE EXTENSION IF NOT EXISTS "pgcrypto";

  -- Restaurar permisos básicos (opcional pero recomendado)
  GRANT USAGE ON SCHEMA public TO postgres;
  GRANT USAGE ON SCHEMA public TO anon;
  GRANT USAGE ON SCHEMA public TO authenticated;
  GRANT USAGE ON SCHEMA public TO service_role;


  -- ==============================================================
  -- SECCIÓN 1: TABLAS MAESTRAS (ESTRUCTURA)
  -- ==============================================================

  CREATE TABLE usuarios_app (
      id SERIAL PRIMARY KEY,
      email VARCHAR(255) UNIQUE NOT NULL,
      rol VARCHAR(50) NOT NULL CHECK (rol IN ('VENTAS', 'OPERACIONES', 'CONTABILIDAD', 'GERENCIA')),
      activo BOOLEAN DEFAULT TRUE,
      fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
      ultimo_acceso TIMESTAMP WITH TIME ZONE
  );

  CREATE TABLE vendedor (
      id_vendedor SERIAL PRIMARY KEY,
      nombre VARCHAR(100) NOT NULL,
      email VARCHAR(255) UNIQUE, -- CRÍTICO: Requerido por login y búsqueda
      estado VARCHAR(20) DEFAULT 'ACTIVO' CHECK (estado IN ('ACTIVO', 'INACTIVO')),
      fecha_ingreso DATE DEFAULT CURRENT_DATE,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE lead (
      id_lead SERIAL PRIMARY KEY,
      nombre_pasajero VARCHAR(255), -- Nuevo campo visual esperado por app
      id_vendedor INTEGER REFERENCES vendedor(id_vendedor) ON DELETE SET NULL,
      numero_celular VARCHAR(20) NOT NULL,
      red_social VARCHAR(50),
      estrategia_venta VARCHAR(50) DEFAULT 'Opciones' CHECK (estrategia_venta IN ('Opciones', 'Matriz', 'General')),
      fecha_creacion TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
      pais_origen VARCHAR(100) DEFAULT 'Nacional' CHECK (pais_origen IN ('Nacional', 'Extranjero', 'Mixto')),
      ultimo_itinerario_id UUID
  );

  CREATE TABLE cliente (
      id_cliente SERIAL PRIMARY KEY,
      id_lead INTEGER REFERENCES lead(id_lead) ON DELETE SET NULL,
      nombre VARCHAR(255), -- Requerido por app
      tipo_cliente VARCHAR(50) DEFAULT 'B2C' CHECK (tipo_cliente IN ('B2C', 'B2B')),
      fecha_registro TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE agencia_aliada (
      id_agencia SERIAL PRIMARY KEY,
      nombre VARCHAR(255) UNIQUE NOT NULL,
      pais VARCHAR(100),
      celular VARCHAR(50),
      fecha_registro TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE tour (
      id_tour SERIAL PRIMARY KEY,
      nombre VARCHAR(255) NOT NULL,
      duracion_horas INTEGER,
      duracion_dias INTEGER,
      precio_adulto_extranjero DECIMAL(10,2),
      precio_adulto_nacional DECIMAL(10,2),
      precio_adulto_can DECIMAL(10,2),
      precio_nino_extranjero DECIMAL(10,2),
      precio_nino_nacional DECIMAL(10,2),
      precio_nino_can DECIMAL(10,2),
      precio_estudiante_extranjero DECIMAL(10,2),
      precio_estudiante_nacional DECIMAL(10,2),
      precio_estudiante_can DECIMAL(10,2),
      precio_pcd_extranjero DECIMAL(10,2),
      precio_pcd_nacional DECIMAL(10,2),
      precio_pcd_can DECIMAL(10,2),
      categoria VARCHAR(50),
      dificultad VARCHAR(20) CHECK (dificultad IN ('FACIL', 'MODERADO', 'DIFICIL', 'EXTREMO')),
      highlights JSONB,
      servicios_incluidos JSONB,
      servicios_no_incluidos JSONB,
      carpeta_img VARCHAR(255),
      hora_inicio TIME, 
      activo BOOLEAN DEFAULT TRUE,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE paquete (
      id_paquete SERIAL PRIMARY KEY,
      nombre VARCHAR(255) NOT NULL,
      descripcion TEXT,
      dias INTEGER NOT NULL,
      noches INTEGER NOT NULL,
      precio_sugerido DECIMAL(10,2),
      temporada VARCHAR(50),
      destino_principal VARCHAR(100),
      activo BOOLEAN DEFAULT TRUE,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE paquete_tour (
      id_paquete INTEGER REFERENCES paquete(id_paquete) ON DELETE CASCADE,
      id_tour INTEGER REFERENCES tour(id_tour) ON DELETE RESTRICT,
      orden INTEGER NOT NULL,
      dia_del_paquete INTEGER,
      PRIMARY KEY (id_paquete, id_tour, orden)
  );
  CREATE TABLE itinerario_digital (
      id_itinerario_digital UUID DEFAULT gen_random_uuid() PRIMARY KEY,
      id_lead INTEGER REFERENCES lead(id_lead) ON DELETE SET NULL,
      id_vendedor INTEGER REFERENCES vendedor(id_vendedor) ON DELETE SET NULL,
      id_paquete INTEGER REFERENCES paquete(id_paquete) ON DELETE SET NULL,
      nombre_pasajero_itinerario VARCHAR(255),
      datos_render JSONB NOT NULL,
      fecha_generacion TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE venta (
      id_venta SERIAL PRIMARY KEY,
      id_cliente INTEGER REFERENCES cliente(id_cliente) ON DELETE RESTRICT,
      id_vendedor INTEGER REFERENCES vendedor(id_vendedor) ON DELETE RESTRICT,
      id_itinerario_digital UUID REFERENCES itinerario_digital(id_itinerario_digital) ON DELETE SET NULL,
      id_paquete INTEGER REFERENCES paquete(id_paquete) ON DELETE SET NULL,
      fecha_venta DATE DEFAULT CURRENT_DATE NOT NULL,
      fecha_inicio DATE,
      fecha_fin DATE,
      precio_total_cierre DECIMAL(10,2) NOT NULL, 
      costo_total DECIMAL(10,2) DEFAULT 0,
      utilidad_bruta DECIMAL(10,2) DEFAULT 0,
      moneda VARCHAR(10) DEFAULT 'USD' CHECK (moneda IN ('USD', 'PEN', 'EUR')),
      tipo_cambio DECIMAL(8,4),
      estado_pago VARCHAR(50) DEFAULT 'PENDIENTE' CHECK (estado_pago IN ('PENDIENTE', 'PARCIAL', 'COMPLETADO', 'REEMBOLSADO')),
      estado_venta VARCHAR(50) DEFAULT 'CONFIRMADO' CHECK (estado_venta IN ('CONFIRMADO', 'EN_VIAJE', 'COMPLETADO', 'CANCELADO')),
      canal_venta VARCHAR(50) DEFAULT 'DIRECTO',
      estado_liquidacion VARCHAR(30) DEFAULT 'PENDIENTE' CHECK (estado_liquidacion IN ('PENDIENTE', 'PARCIAL', 'FINALIZADO')),
      id_agencia_aliada INTEGER REFERENCES agencia_aliada(id_agencia),
      tour_nombre VARCHAR(255),
      num_pasajeros INTEGER DEFAULT 1, 
      cancelada BOOLEAN DEFAULT FALSE,
      fecha_cancelacion TIMESTAMP WITH TIME ZONE,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE venta_tour (
      id_venta INTEGER REFERENCES venta(id_venta) ON DELETE CASCADE,
      n_linea INTEGER NOT NULL,
      id_tour INTEGER REFERENCES tour(id_tour) ON DELETE RESTRICT,
      fecha_servicio DATE NOT NULL,
      hora_inicio TIME,
      precio_applied DECIMAL(10,2),
      costo_applied DECIMAL(10,2),
      moneda_costo VARCHAR(10) DEFAULT 'USD',
      id_proveedor INTEGER, -- Definido más adelante como FK
      cantidad INTEGER DEFAULT 1,
      punto_encuentro VARCHAR(255),
      observacion TEXT,
      id_itinerario_dia_index INTEGER,
      estado_servicio VARCHAR(30) DEFAULT 'PENDIENTE' CHECK (estado_servicio IN ('PENDIENTE', 'CONFIRMADO', 'EN_CURSO', 'COMPLETADO', 'CANCELADO')),
      -- Flujo de Caja Maestro (Liquidación + Requerimientos + Endosos)
      estado_pago_operativo VARCHAR(20) DEFAULT 'NO_REQUERIDO' CHECK (estado_pago_operativo IN ('NO_REQUERIDO', 'PENDIENTE', 'PAGADO')),
      datos_pago_operativo TEXT, -- Cuentas, Yape, Plin del proveedor o guía
      es_endoso BOOLEAN DEFAULT FALSE, -- Flag para identificar si fue tercerizado
      costo_unitario DECIMAL(10,2) DEFAULT 0,
      cantidad_items INTEGER DEFAULT 1,
      precio_vendedor DECIMAL(10,2) DEFAULT 0, -- Precio proyectado por el vendedor (referencia)
      PRIMARY KEY (id_venta, n_linea)
  );
  
  CREATE TABLE venta_item_ingreso (
      id_item_ingreso SERIAL PRIMARY KEY,
      id_venta INTEGER REFERENCES venta(id_venta) ON DELETE CASCADE,
      descripcion VARCHAR(255) NOT NULL, -- Ej: 'Pax Nacional', 'Pax Extranjero', 'Suplemento', etc.
      cantidad INTEGER NOT NULL DEFAULT 1,
      precio_unitario DECIMAL(10,2) NOT NULL,
      subtotal DECIMAL(10,2) GENERATED ALWAYS AS (cantidad * precio_unitario) STORED,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE pago (
      id_pago SERIAL PRIMARY KEY,
      id_venta INTEGER REFERENCES venta(id_venta) ON DELETE CASCADE,
      fecha_pago DATE DEFAULT CURRENT_DATE NOT NULL,
      monto_pagado DECIMAL(10,2) NOT NULL CHECK (monto_pagado > 0),
      moneda VARCHAR(10) DEFAULT 'USD' CHECK (moneda IN ('USD', 'PEN', 'EUR')),
      tasa_cambio DECIMAL(10,4) DEFAULT 1.0,
      monto_moneda_venta DECIMAL(10,2), -- El monto convertido a la moneda de la venta
      metodo_pago VARCHAR(50) CHECK (metodo_pago IN ('EFECTIVO', 'TRANSFERENCIA', 'TARJETA', 'PAYPAL', 'YAPE', 'PLIN', 'OTRO')),
      tipo_pago VARCHAR(50) CHECK (tipo_pago IN ('ADELANTO', 'SALDO', 'TOTAL', 'PARCIAL', 'REEMBOLSO')),
      tipo_comprobante VARCHAR(50) DEFAULT 'RECIBO' CHECK (tipo_comprobante IN ('BOLETA', 'FACTURA', 'RECIBO', 'RECIBO SIMPLE', 'SIN_COMPROBANTE')),
      created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE IF NOT EXISTS paquete_personalizado (
      id_paquete_personalizado UUID PRIMARY KEY DEFAULT gen_random_uuid(),
      nombre TEXT NOT NULL,
      itinerario JSONB NOT NULL,
      creado_por TEXT, -- Email del vendedor
      es_publico BOOLEAN DEFAULT TRUE,
      created_at TIMESTAMPTZ DEFAULT now()
  );

  CREATE TABLE IF NOT EXISTS plantilla_servicio (
      id SERIAL PRIMARY KEY,
      titulo TEXT NOT NULL,
      descripcion TEXT,
      costo_nac DECIMAL(10,2) DEFAULT 0,
      costo_ext DECIMAL(10,2) DEFAULT 0,
      categoria VARCHAR(50) DEFAULT 'OTROS',
      icono VARCHAR(50) DEFAULT 'default_in'
  );

  INSERT INTO plantilla_servicio (titulo, descripcion, icono) VALUES 
  ('Día Libre / Descanso', 'Día destinado al descanso o actividades personales. No incluye tours.', 'calendario'),
  ('Traslado Aeropuerto ➡️ Hotel', 'Recepción en el aeropuerto y traslado en unidad privada hacia el hotel.', 'transporte'),
  ('Traslado Hotel ➡️ Aeropuerto', 'Traslado desde el hotel hacia el aeropuerto para su vuelo de salida.', 'transporte');

  CREATE TABLE pasajero (
      id_pasajero SERIAL PRIMARY KEY,
      id_venta INTEGER REFERENCES venta(id_venta) ON DELETE CASCADE,
      nombre_completo VARCHAR(255) NOT NULL,
      nacionalidad VARCHAR(100),
      numero_documento VARCHAR(50),
      tipo_documento VARCHAR(20) CHECK (tipo_documento IN ('DNI', 'PASAPORTE', 'CARNET_EXTRANJERIA', 'DIE')),
      fecha_nacimiento DATE,
      genero VARCHAR(20),
      cuidados_especiales TEXT,
      es_principal BOOLEAN DEFAULT FALSE,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
  );

  CREATE TABLE proveedor (
      id_proveedor SERIAL PRIMARY KEY,
      nombre_comercial VARCHAR(255) NOT NULL,
      servicios_ofrecidos TEXT[], 
      contacto_telefono VARCHAR(20),
      pais VARCHAR(100) DEFAULT 'Perú',
      activo BOOLEAN DEFAULT TRUE,
      created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
      updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
  );

  -- Vincular FK faltantes
  ALTER TABLE venta_tour ADD CONSTRAINT fk_proveedor_tour FOREIGN KEY (id_proveedor) REFERENCES proveedor(id_proveedor) ON DELETE SET NULL;

  CREATE TABLE venta_servicio_proveedor (
      id SERIAL PRIMARY KEY,
      id_venta INTEGER,
      n_linea INTEGER,
      id_proveedor INTEGER REFERENCES proveedor(id_proveedor) ON DELETE RESTRICT,
      tipo_servicio VARCHAR(50), 
      costo_unitario DECIMAL(10,2) NOT NULL,
      moneda VARCHAR(10) DEFAULT 'USD',
      cantidad_pax INTEGER DEFAULT 1,

      created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (id_venta, n_linea) REFERENCES venta_tour(id_venta, n_linea) ON DELETE CASCADE,
      UNIQUE(id_venta, n_linea, tipo_servicio)
  );

  CREATE TABLE pago_operativo (
      id_pago_op SERIAL PRIMARY KEY,
      id_proveedor INTEGER REFERENCES proveedor(id_proveedor) ON DELETE CASCADE,
      id_venta INTEGER REFERENCES venta(id_venta) ON DELETE SET NULL,
      n_linea INTEGER, -- Para vincular a un servicio específico
      monto_pagado DECIMAL(10,2) NOT NULL CHECK (monto_pagado > 0),
      moneda VARCHAR(10) DEFAULT 'USD' CHECK (moneda IN ('USD', 'PEN', 'EUR')),
      tasa_cambio DECIMAL(10,4) DEFAULT 1.0, -- TC para convertir 'monto_pagado' a moneda de la deuda
      monto_en_moneda_costo DECIMAL(10,2) NOT NULL, -- Cuánto baja de la deuda original
      fecha_pago DATE DEFAULT CURRENT_DATE NOT NULL,
      metodo_pago VARCHAR(50) CHECK (metodo_pago IN ('EFECTIVO', 'TRANSFERENCIA', 'YAPE', 'PLIN', 'TARJETA', 'OTRO')),
      comprobante_url TEXT, -- Link al voucher/foto
      observaciones TEXT,
      id_usuario_registro INTEGER REFERENCES usuarios_app(id),
      created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
      FOREIGN KEY (id_venta, n_linea) REFERENCES venta_tour(id_venta, n_linea) ON DELETE SET NULL
  );


  -- 2.1. USUARIOS Y VENDEDORES
  -- Los emails deben coincidir para que el sistema vincule el login con el vendedor asignado.
  INSERT INTO usuarios_app (email, rol) VALUES 
  ('angel@latitudvcp.com', 'VENTAS'),
  ('abel@latitudvcp.com', 'VENTAS'),
  ('maria@latitudvcp.com', 'OPERACIONES'),
  ('elizabeth@latitudvcp.com', 'CONTABILIDAD'),
  ('vanessa@latitudvcp.com', 'GERENCIA'),
  ('henrry@latitudvcp.com', 'GERENCIA');

  INSERT INTO vendedor (nombre, email) VALUES
  ('Angel', 'angel@latitudvcp.com'),
  ('Abel', 'abel@latitudvcp.com'),
  ('Maria', 'maria@latitudvcp.com'),
  ('Vanessa', 'vanessa@latitudvcp.com'),
  ('Henrry', 'henrry@latitudvcp.com');

  -- 2.2. AGENCIAS ALIADAS (B2B)
  INSERT INTO agencia_aliada (nombre, pais, celular) VALUES 
  ('Ulises Viaje', 'Argentina', '+54 9 3534 28-1109'),
  ('Like Travel', 'Argentina', '+54 9 3517 64-3797'),
  ('Kuna Travel', 'Mexico', '+52 1 614 277 7793'),
  ('Guru Destinos', 'Argentina', '+54 9 11 6458-9079'),
  ('Hector', 'Mexico', '+52 1 33 2492 7483'),
  ('Rogelio', 'Brazil', '+55 48 8424-1401'),
  ('Willian', 'Bolivia', '+591 75137410'),
  ('Cave', 'Peru', '+51 982 167 776');

  -- 2.3. CATÁLOGO DE TOURS
  INSERT INTO tour (
    nombre, duracion_horas, duracion_dias, precio_adulto_extranjero, precio_adulto_nacional,
    categoria, dificultad, highlights, servicios_incluidos, servicios_no_incluidos,
    carpeta_img, hora_inicio, activo
  ) VALUES 
  (
    'RECEPCION - CUSCO, CITY TOUR',
    4, 1, 42.00, 105.00,
    'RECEPCION - CUSCO, CITY TOUR', 'FACIL',
    '{"itinerario": "A la llegada a Cusco, nuestro personal realiza el traslado al ***hotel seleccionado***, donde se ofrece un reconfortante ***mate de coca o muña*** para ayudar a la aclimatación a la altura. Luego tendrán tiempo para ***descansar y relajarse*** antes de iniciar las actividades programadas en la ciudad.\n\nPosteriormente realizamos la ***Excursión City Tour*** visitando el ***Qoricancha***, antiguo ***Templo Mayor inca***, y los impresionantes complejos arqueológicos de ***Sacsayhuamán***, ***Qenqo***, ***Tambomachay*** y ***Puka Pukara***, destacados por su valor ceremonial, hidráulico y militar. Finalizamos el recorrido cerca de la ***Plaza Mayor de Cusco***, facilitando el retorno al ***hotel***"}'::jsonb,
    '{"incluye": ["Recojo de Hotel", "Boleto Turístico", "Ticket a Qoricancha", "Guía Profesional", "Transporte Turístico"]}'::jsonb,
    '{"no_incluye": ["Hospedaje", "Gastos Extras", "Alimentacion"]}'::jsonb,
    'city_tour_cusco', '09:00:00', TRUE
  ),
  (
    'VALLE VIP CONEXIÓN MACHU PICCHU',
    8, 1, 44.00, 115.00,
    'FULL DAY', 'MODERADO',
    '{"itinerario": "Después del desayuno, iniciamos la ruta por el ***Valle Sagrado de los Incas*** visitando ***Chinchero***, donde conoceremos un antiguo ***palacio inca***, su ***iglesia colonial*** y un tradicional ***centro textil***. Continuamos hacia ***Moray***, famoso por sus ***terrazas circulares agrícolas***, y luego descendemos a las impresionantes ***Salineras de Maras***, con miles de pozos de sal aún en funcionamiento.\n\nEl recorrido prosigue hacia el valle de ***Urubamba*** para disfrutar de un ***almuerzo buffet***. Posteriormente visitamos ***Ollantaytambo***, conocida como la ***última ciudad inca viviente***, y nos dirigimos a la estación para abordar el ***tren turístico*** rumbo a ***Aguas Calientes*** y nos trasladamos al ***hotel*** para pasar la noche."}'::jsonb,
    '{"incluye": ["Recojo de Hotel", "Almuerzo Buffet", "Transporte Turistico", "Boleto Turistico", "Ingreso a Salineras", "Ticket de Tren Turistico", "Guia Profesional"]}'::jsonb,
    '{"no_incluye": ["Gastos Extras", "Hospedaje", "Aliementación"]}'::jsonb,
    'valle_sagrado_vip', '06:30:00', TRUE
  ),
  (
    'VISITA A MACHU PICCHU',
    8, 1, 208.00, 562.00,
    'FULL DAY', 'MODERADO',
    '{"itinerario": "Después del desayuno, abordamos el bus hacia la impresionante ***Ciudadela de Machu Picchu***, donde realizamos una completa ***visita guiada*** por sus principales sectores arqueológicos, plazas y templos, descubriendo la historia y el legado de esta ***maravilla del mundo***.\n\nAl finalizar el recorrido, descendemos a ***Aguas Calientes*** para tiempo libre y almuerzo en restaurantes locales. Por la tarde, abordamos el ***tren turístico*** de retorno, pasando por ***Ollantaytambo*** y continuando el traslado terrestre hasta ***Cusco***, donde finaliza esta inolvidable experiencia cultural."}'::jsonb,
    '{"incluye": ["Bus de subida y bajada", "Ingreso a Machu Picchu", "Ticket de Tren Turístico", "Transporte Ollanta -Cusco", "Guía Profesional"]}'::jsonb,
    '{"no_incluye": ["Hospedaje","Alimentación", "Gastos Extras"]}'::jsonb,
    'machu_picchu_full_day', '05:00:00', TRUE
  ),
  (
    'CITY TOUR CUSCO',
    4, 1, 31.34, 75.00,
    'CITY TOUR', 'FACIL',
    '{"itinerario": "Iniciamos el ***City Tour por Cusco*** con la visita al ***Qoricancha***, antiguo ***Templo del Sol*** y uno de los centros religiosos más importantes del mundo inca. Luego nos dirigimos a ***Sacsayhuamán***, majestuoso complejo ceremonial que impresiona por sus ***colosales muros de piedra*** y la extraordinaria ***ingeniería ancestral***.\n\nEl recorrido continúa hacia ***Qenqo***, centro de ***rituales ceremoniales***, ***Tambomachay***, santuario dedicado al ***agua sagrada***, y ***Puka Pukara***, fortaleza de ***control estratégico***. Finalizamos cerca de la ***Plaza Mayor***, facilitando el retorno al ***hotel***."}'::jsonb,
    '{"incluye": ["Recojo de Hotel", "Boleto Turístico", "Ticket a Qoricancha", "Guía Profesional", "Transporte Turístico"]}'::jsonb,
    '{"no_incluye": ["Hospedaje", "Gastos Extras"]}'::jsonb,
    'city_tour_cusco', '09:00:00', TRUE
  ),
  (
    'VALLE SAGRADO VIP',
    8, 1, 43.28, 115.00,
    'FULL DAY', 'MODERADO',
    '{"itinerario": "Después del desayuno, iniciamos una experiencia por el ***Valle Sagrado de los Incas*** visitando ***Chinchero***, donde conoceremos un antiguo ***palacio inca***, su ***iglesia colonial*** y un tradicional ***centro textil***. Continuamos hacia ***Moray***, famoso por sus ***terrazas circulares*** utilizadas como laboratorio agrícola en época inca, y luego descendemos a las impresionantes ***Salineras de Maras***, con miles de pozos de sal aún en uso.\n\nSeguimos el recorrido hacia el valle de ***Urubamba*** para disfrutar de un ***almuerzo buffet***. Posteriormente visitamos ***Ollantaytambo***, conocida como la ***última ciudad inca viviente***, y finalizamos en ***Pisac***, donde exploramos sus ***andenes arqueológicos*** y el colorido ***mercado artesanal***. Retorno a Cusco al finalizar la jornada."}'::jsonb,
    '{"incluye": ["Recojo del Hotel", "Almuerzo Buffett", "Transporte Turístico", "Guía Profesional", "Boleto Turístico", "Ingreso a Salineras"]}'::jsonb,
    '{"no_incluye": ["Gastos Extras", "Hospedaje", "Alimentación"]}'::jsonb,
    'valle_sagrado_vip', '06:30:00', TRUE
  ),
  (
    'MACHU PICCHU FULL DAY',
    8, 1, 207.28, 561.25,
    'FULL DAY', 'MODERADO',
    '{"itinerario": "Iniciamos la experiencia con el traslado desde Cusco hacia la estación de tren en ***Ollantaytambo***, donde abordamos el ***tren turístico*** con destino al pueblo de ***Aguas Calientes***. A la llegada, nuestro ***guía especializado*** los recibirá para dirigirnos a la estación de buses y ascender hacia el impresionante ***Santuario de Machu Picchu***, una de las ***maravillas del mundo***.\n\nEn la ciudadela, realizamos una ***visita guiada completa*** recorriendo los principales sectores arqueológicos y espacios ceremoniales. Al finalizar, descendemos a ***Aguas Calientes*** para tiempo libre y alimentación. Posteriormente retornamos en tren a ***Ollantaytambo*** y continuamos el traslado hasta su ***hotel en Cusco***."}'::jsonb,
    '{"incluye": ["Recojo del hotel", "Ingreso a Machu Picchu", "Ticket de Tren Turístico", "Transporte Ollanta -Cusco", "Guía Profesional"]}'::jsonb,
    '{"no_incluye": ["Alimentación", "Gastos Extras", "Hospedaje"]}'::jsonb,
    'machu_picchu_full_day', '08:00:00', TRUE
  ),
  (
    'LAGUNA HUMANTAY',
    12, 1, 22.39, 75.00,
    'NATURALEZA', 'MODERADO',
    '{"itinerario": "Iniciamos la aventura con el traslado desde Cusco hacia el pueblo de ***Mollepata***, donde disfrutamos de un ***desayuno tradicional*** antes de continuar hasta ***Soraypampa***, punto de inicio de la caminata. Desde allí emprendemos el ascenso hacia la impresionante ***Laguna Humantay***, rodeada de paisajes andinos y dominada por la majestuosa ***montaña Humantay***.\n\nDurante la visita, nuestro ***guía especializado*** nos explicará la importancia natural y cultural del lugar, así como las vistas del ***nevado Salkantay***, considerado una ***montaña sagrada***. Tras la exploración, retornamos a Soraypampa para disfrutar de un ***almuerzo reconfortante*** y luego regresamos a ***Cusco***, concluyendo esta inolvidable experiencia de alta montaña."}'::jsonb,
    '{"incluye": ["Recojo del hotel", "Ticket de ingreso a laguna", "Alimentación", "Botiquín de primeros Auxilios", "Guía Profesional", "Transporte Turístico"]}'::jsonb,
    '{"no_incluye": ["Gastos Extras", "Caballos", "Hospedaje"]}'::jsonb,
    'laguna_humantay', '04:00:00', TRUE
  ),
  (
    'MONTAÑA DE COLORES',
    14, 1, 23.88, 80.00,
    'AVENTURA', 'DIFICIL',
    '{"itinerario": "Iniciamos la excursión con el traslado desde Cusco hacia las faldas del ***nevado Ausangate***, disfrutando de los espectaculares ***paisajes altoandinos***. Al llegar al punto de inicio, se brinda un ***desayuno ligero*** y una charla introductoria antes de comenzar la caminata rumbo al ***Cerro Colorado – Vinicunca***, atravesando ***caseríos tradicionales*** y zonas de pastoreo de ***alpacas y llamas***.\n\nAl alcanzar la ***Montaña de Colores***, admiramos sus impresionantes ***tonalidades naturales*** y las vistas del majestuoso ***Apu Ausangate***. Luego descendemos para disfrutar de un ***almuerzo reconfortante*** y retornamos a ***Cusco***, concluyendo esta inolvidable experiencia andina."}'::jsonb,
    '{"incluye": ["Recojo del Hotel", "Desayuno | Almuerzo", "Botiquín de Primeros Auxilios", "Guía Profesional", "Transporte Turistico", "Tickets de Ingreso a la montaña", "Bastones de Trekking"]}'::jsonb,
    '{"no_incluye": ["Gastos Extras", "Caballos", "Cuatrimotos", "Hospedaje"]}'::jsonb,
    'montana_de_colores', '04:00:00', TRUE
  ),
  (
    'PALCCOYO',
    10, 1, 28.39, 95.00,
    'AVENTURA', 'MODERADO',
    '{"itinerario": "Iniciamos la experiencia con el traslado desde Cusco hacia el poblado de ***Cusipata***, donde disfrutamos de un ***desayuno tradicional***. En el trayecto apreciamos el ***puente colonial de Checacupe*** y un criadero de ***camélidos sudamericanos***, antes de continuar hacia el punto de inicio de la caminata en un entorno netamente andino.\n\nLa caminata es ***sencilla y panorámica***, recorriendo el impresionante ***bosque de piedras*** y disfrutando de vistas de majestuosos ***nevados*** como el ***Ausangate***. Visitamos las fascinantes ***Montañas de Colores de Palcoyo***, tres formaciones multicolores únicas. Finalizamos con un ***almuerzo buffet novo-andino*** y retornamos a ***Cusco***."}'::jsonb,
    '{"incluye": ["Transporte Turístico", "Desayuno | Almuerzo", "Botiquín de Primeros Auxilios"]}'::jsonb,
    '{"no_incluye": ["Gastos extras", "Caballos", "Hotel"]}'::jsonb,
    'palccoyo', '04:00:00', TRUE
  ),
  (
    'WAQRAPUKARA',
    13, 1, 26.87, 100.00,
    'AVENTURA', 'MODERADO',
    '{"itinerario": "Iniciamos la excursión con el traslado desde Cusco hacia el poblado de ***Cusipata***, donde disfrutamos de un ***desayuno tradicional*** antes de continuar el viaje hacia ***Santa Lucía***. Desde este punto comenzamos una caminata rodeada de ***valles andinos***, apreciando la ***flora y fauna local*** y espectaculares paisajes naturales durante el recorrido.\n\nEn el trayecto realizamos una pausa en el punto más alto para disfrutar del entorno y tomar fotografías, antes de llegar a ***Waqrapukara***, antiguo ***santuario inca*** de gran valor ***político y religioso***. Tras la visita guiada, retornamos para disfrutar de un ***almuerzo reconfortante*** y regresamos a ***Cusco***, concluyendo la experiencia."}'::jsonb,
    '{"incluye": ["Transporte Turistico", "Guia", "Asistencia","Desayuno|Almuerzo", "Recojo de Hotel", "Ticket de Ingreso", "Botiquin de Primeros auxilios", "Bastones de Trekking", "Balon de Oxigeno"]}'::jsonb,
    '{"no_incluye": ["Gastos Extras", "Caballos", "Hospedaje", "Cena"]}'::jsonb,
    'waqrapukara', '03:00:00', TRUE
  ),
  (
    'SIETE LAGUNAS AUSANGATE',
    14, 1, 26.87, 90.00,
    'NATURALEZA', 'MODERADO',
    '{"itinerario": "Iniciamos la aventura con el traslado desde Cusco hacia el pintoresco poblado de ***Pacchanta***, donde disfrutamos de un ***desayuno andino*** antes de comenzar la caminata. Desde allí emprendemos un ascenso gradual visitando las impresionantes ***lagunas altoandinas***, cada una con tonalidades ***azules, turquesas y verdes*** que destacan por su belleza natural y pureza.\n\nDurante el recorrido observamos ***fauna andina*** como alpacas, llamas y aves silvestres, con vistas permanentes del majestuoso ***nevado Ausangate***. Al finalizar la caminata, retornamos a ***Pacchanta*** para disfrutar de un ***almuerzo típico*** y relajarnos en sus ***aguas termales***, antes de emprender el regreso a ***Cusco***."}'::jsonb,
    '{"incluye": ["Transporte Turística", "Desayuno | Almuerzo", "Botiquín de Primeros Auxilios", "Guía Profesional", "Ticket de Ingreso"]}'::jsonb,
    '{"no_incluye": ["Gastos extras", "Caballos", "Hospedaje"]}'::jsonb,
    'siete_lagunas_ausangate', '04:00:00', TRUE
  ),
  (
    'VALLE SUR',
    6, 1, 32.24, 75.00,
    'CULTURA', 'FACIL',
    '{"itinerario": "Iniciamos el recorrido por la ***zona sur del Cusco*** visitando ***Tipón***, reconocido como el ***Templo del Agua*** por su avanzado sistema hidráulico inca, y continuamos hacia ***Pikillacta***, importante complejo ***arqueológico preinca*** que destaca por su planificación urbana. Luego visitamos la iglesia de ***Andahuaylillas***, conocida como la ***Capilla Sixtina de América*** por su impresionante arte colonial.\n\nLa experiencia se complementa con la ***gastronomía tradicional*** de la región, degustando el famoso ***chicharrón de Saylla***, el delicioso ***cuy al horno*** y el tradicional ***pan chuta de Oropesa***. Finalizamos el tour tras una jornada cultural y culinaria inolvidable."}'::jsonb,
    '{"incluye": ["Recojo del hotel", "Transporte Turístico", "Guía Profesional", "Tickets"]}'::jsonb,
    '{"no_incluye": ["Gastos Extras", "Alimentación"]}'::jsonb,
    'valle_sur', '09:00:00', TRUE
  ),
  (
    'MORADA DE LOS DIOSES',
    4, 1, 11.94, 35.00,
    'TURISMO', 'FACIL',
    '{"itinerario": "Iniciamos la experiencia con el traslado desde Cusco hacia el poblado de ***Sencca***, ubicado al norte de la ciudad, desde donde disfrutamos de una ***vista panorámica inicial*** del complejo escultórico. Tras una breve caminata, llegamos a las imponentes ***esculturas contemporáneas*** inspiradas en la ***cosmovisión andina*** y sus principales deidades ancestrales.\n\nDurante la visita interactuamos con representaciones como la ***Pachamama***, el ***Dios Wiracocha***, el ***Portal Inti*** y el ***Puma***, conociendo sus ***mitos y leyendas***. Finalizamos en el ***mirador de la Pachamama***, que ofrece una espectacular ***vista panorámica del Cusco***, antes del retorno a la ciudad."}'::jsonb,
    '{"incluye": ["Recojo del Hotel", "Ticket de Ingreso", "Guia Profesional", "Transporte Turistico"]}'::jsonb,
    '{"no_incluye": ["Gastos Extras", "Alimentación", "Hospedaje"]}'::jsonb,
    'morada_de_los_dioses', '09:00:00', TRUE
  ),
  (
    'RUTA DEL SOL (Cusco - Puno)',
    10, 1, 53.82, 177.30,
    'TURISMO', 'FACIL',
    '{"itinerario": "Tras el desayuno, iniciamos el viaje desde Cusco recorriendo el ***corredor sur del altiplano*** en una jornada cultural con varias paradas guiadas. Visitamos la iglesia de ***Andahuaylillas***, conocida como la ***Capilla Sixtina de América***, y el impresionante templo inca de ***Raqchi***, uno de los complejos arqueológicos más importantes de la región.\n\nContinuamos hacia ***Sicuani*** para disfrutar de un ***almuerzo buffet*** y luego ascendemos al ***Paso de La Raya***, el punto más alto del recorrido. Finalizamos con la visita al ***Museo Inca Aymara de Pukara*** antes de arribar a ***Puno***, donde realizamos el traslado al ***hotel*** para pasar la noche."}'::jsonb,
    '{"incluye": ["Transporte Turistico", "Boleto Turistico", "Guia Profesional", "Almuerzo"]}'::jsonb,
    '{"no_incluye": ["Gastos Extras", "Alimentación", "Hospedaje"]}'::jsonb,
    'ruta_del_sol_cusco_puno', '06:00:00', TRUE
  ),
  (
    'RUTA DEL SOL (Puno - Cusco)',
    10, 1, 53.82, 177.30,
    'TURISMO', 'FACIL',
    '{"itinerario": "Disfrutarán del ***desayuno en el hotel*** antes de iniciar el recorrido turístico en bus desde ***Puno hacia Cusco*** por el corredor sur andino. Durante el trayecto se realizarán paradas culturales, iniciando con la visita al ***Museo de Pukara***, donde se apreciarán ***esculturas líticas y cerámicas preincas***. Luego se visitará el ***Abra de la Raya***, el punto más alto del recorrido, y la ciudad de ***Sicuani***, donde se disfrutará de un ***almuerzo buffet con productos locales***.\n\nContinuando el viaje, se conocerá el impresionante complejo arqueológico de ***Raqchi***, un ***templo inca dedicado al dios Wiracocha***, destacado por su arquitectura en adobe y recintos circulares. Posteriormente se visitará la iglesia colonial de ***Andahuaylillas***, conocida como la ***Capilla Sixtina de América*** por su extraordinaria decoración artística. Finalmente, se arribará a la ciudad del ***Cusco***, donde nuestro personal realizará la ***recepción y traslado al hotel seleccionado***."}'::jsonb,
    '{"incluye": ["Transporte Turistico", "Boleto Turistico", "Guia Profesional"]}'::jsonb,
    '{"no_incluye": ["Gastos Extras", "Alimentación"]}'::jsonb,
    'ruta_del_sol_cusco_puno', '06:00:00', TRUE
  ),
  (
    'SOBREVUELO LINEAS DE NAZCA',
    1, 1, 107.99, 361.75,
    'TURISMO', 'FACIL',
    '{"itinerario": "Después del desayuno, realizamos el traslado al aeródromo local para disfrutar de un espectacular ***sobrevuelo a las Líneas de Nazca***. Desde el aire observamos los enigmáticos ***geoglifos preincas*** que representan figuras de animales y plantas, como el ***colibrí***, el ***mono*** y la ***araña***, además de líneas geométricas que forman un misterioso paisaje grabado en la pampa.\n\nFinalizada la experiencia aérea, nos dirigimos al terminal terrestre para continuar el viaje hacia ***Arequipa***. A la llegada, nuestro personal los recibe y realiza el traslado al ***hotel seleccionado***, culminando una jornada llena de ***historia, misterio y cultura ancestral***."}'::jsonb,
    '{"incluye": ["Recojo de Hotel", "Transporte Regular", "Tickets", "Guia Profesional"]}'::jsonb,
    '{"no_incluye": ["Gastos Extras", "Alimentacion", "Tasa Aeropuertaria"]}'::jsonb,
    'sobrevuelo_lineas_de_nazca_nazca', '07:00:00', TRUE
  ),
  (
    'SOBREVUELO LINEAS DE NAZCA - AREQUIPA',
    1, 1, 141.0, 471.0,
    'TURISMO', 'FACIL',
    '{"itinerario": "Después del ***desayuno en el hotel***, se realizará el traslado al aeródromo local para abordar la avioneta y disfrutar del ***sobrevuelo a las Líneas de Nazca***, una de las manifestaciones arqueológicas más enigmáticas del mundo. Durante la experiencia aérea se podrán apreciar los ***antiguos geoglifos***, figuras de animales, plantas y formas geométricas trazadas sobre el desierto y conservadas por siglos.\n\nFinalizada esta experiencia única, se efectuará el traslado al terminal terrestre para iniciar el ***viaje hacia la ciudad de Arequipa***. A la llegada, nuestro personal estará esperando para brindarles la ***bienvenida y el traslado*** hacia su hotel, donde podrán descansar y continuar con su itinerario."}'::jsonb,
    '{"incluye": ["Recojo de Hotel", "Transporte Regular", "Tickets", "Guia Profesional"]}'::jsonb,
    '{"no_incluye": ["Gastos Extras", "Alimentacion", "Tasa Aeropuertaria"]}'::jsonb,
    'sobrevuelo_lineas_de_nazca_nazca', '07:00:00', TRUE
  );
  INSERT INTO tour (
    nombre, duracion_horas, duracion_dias, precio_adulto_extranjero, precio_adulto_nacional,
    categoria, dificultad, highlights, servicios_incluidos, servicios_no_incluidos,
    carpeta_img, hora_inicio, activo
  ) VALUES 
  (
    'LIMA - ISLAS BALLESTAS - HUACACHINA',
    15, 1, 44.78, 150.0,
    'TURISMO', 'FACIL',
    '{"itinerario": "Después del desayuno, nos trasladamos al puerto de ***Paracas*** para iniciar la excursión a las ***Islas Ballestas***, pasando por el enigmático ***Candelabro***, una gigantesca figura trazada en la ladera del desierto. Durante el recorrido marítimo observamos ***lobos marinos***, ***pingüinos*** y diversas ***aves marinas*** en su hábitat natural.\n\nPor la tarde visitamos el ***Oasis de Huacachina***, un hermoso lago rodeado de impresionantes ***dunas de arena***. Aquí disfrutamos del entorno natural y de actividades como el ***sandboarding***. Finalizamos la jornada con el retorno hacia ***Lima***."}'::jsonb,
    '{"incluye": ["Recojo del Hotel en Lima", "Transporte Turistico", "Boleto de Ingreso a todos los atractivos", "Guia Profesional", "Lancha", "Tubular y Sandboarding"]}'::jsonb,
    '{"no_incluye": ["Hospedaje en Lima Miraflores", "Alimentación", "Gastos Extras"]}'::jsonb,
    'paracas_y_huacachina', '03:00:00', TRUE
  ),
  (
    'MARAS, MORAY Y SALINERAS',
    6, 1, 34.33, 85.00,
    'TURISMO', 'FACIL',
    '{"itinerario": "Iniciamos el recorrido en ***Chinchero***, conocida como la ***Cuna del Arcoíris***, un pintoresco pueblo colonial donde visitamos un ***taller textil tradicional*** para conocer las técnicas ancestrales de tejido y el uso de ***tintes naturales*** obtenidos de plantas y minerales. Luego continuamos hacia ***Moray***, un sorprendente ***laboratorio agrícola inca*** conformado por terrazas circulares que demuestran la avanzada ***ingeniería ancestral***.\n\nEl tour prosigue hacia el pueblo colonial de ***Maras*** y las impresionantes ***Salineras de Maras***, un conjunto de miles de pozas de ***sal rosada*** que forman uno de los paisajes más emblemáticos del ***Valle Sagrado***. Finalizamos con el retorno a ***Cusco***, donde dispondrán de ***tiempo libre*** para actividades personales y compras."}'::jsonb,
    '{"incluye": ["Recojo del Hotel", "Ticket de Ingreso", "Ticket Salineras", "Guia Profesional", "Transporte Turistico"]}'::jsonb,
    '{"no_incluye": ["Gastos Extras"]}'::jsonb,
    'maras_moray_y_salineras', '06:30:00', TRUE
  ),
  (
    'CUATRIMOTO HUAYPO Y SALINERAS',
    5, 1, 32.84, 110.0,
    'TURISMO', 'FACIL',
    '{"itinerario": "Iniciamos la experiencia con el traslado desde Cusco hacia el poblado de ***Cruz Pata***, donde recibimos una breve ***inducción de manejo*** antes de comenzar la aventura en ***cuatrimotos***. El recorrido nos conduce hacia la tranquila ***Laguna de Huaypo***, donde disfrutamos de tiempo libre para apreciar el paisaje natural y el entorno andino.\n\nContinuamos la ruta pasando por el pintoresco pueblo colonial de ***Maras*** y visitamos las emblemáticas ***Salineras de Maras***, reconocidas por sus terrazas de ***sal natural***. Al finalizar, retornamos a la base para el traslado hacia ***Ollantaytambo***, donde abordamos el ***tren turístico*** con destino a ***Aguas Calientes***, lugar donde pasaremos la noche."}'::jsonb,
    '{"incluye": ["Recojo del Hotel", "Botiquin de Primeros Auxilios", "Guia Profesional", "Transporte Turistico", "Cuatrimotos", "Transporte Maras - Ollantaytambo", "Ingreso a Salineras", "Hospedaje en Aguas Calientes"]}'::jsonb,
    '{"no_incluye": ["Gastos Extras"]}'::jsonb,
    'cuatrimoto_huaypo_y_salineras', '13:00:00', TRUE
  ),
  (
    'CUATRIMOTO MONTAÑA DE COLORES',
    14, 1, 52.24, 175.0,
    'TURISMO', 'FACIL',
    '{"itinerario": "Iniciamos la experiencia con el traslado desde Cusco hacia las faldas del ***nevado Ausangate***, donde disfrutamos de un ***desayuno andino*** rodeados de espectaculares ***paisajes de alta montaña***. Luego llegamos a ***Japura***, punto de inicio de la aventura, donde recibimos las indicaciones para conducir las ***cuatrimotos*** antes de comenzar el recorrido.\n\nLa ruta en cuatrimotos nos lleva hasta la impresionante ***Montaña de Colores – Vinicunca***, atravesando paisajes andinos con ***llamas y alpacas***. En el ***Cerro Colorado*** apreciamos sus ***tonalidades naturales*** y la vista del majestuoso ***Apu Ausangate***. Tras el recorrido, retornamos a la base y regresamos a ***Cusco***."}'::jsonb,
    '{"incluye": ["Recojo del Hotel", "Ticket de Ingreso a la Montaña", "Desayuno | Almuerzo", "Botiquin de Primeros Auxilios", "Guia Profesional", "Transporte Turistico", "Cuatrimoto"]}'::jsonb,
    '{"no_incluye": ["Gastos Extras", "Caballos"]}'::jsonb,
    'cuatrimoto_montana_de_colores_valle_rojo', '04:00:00', TRUE
  );

  INSERT INTO tour (
    nombre, duracion_horas, duracion_dias, precio_adulto_extranjero, precio_adulto_nacional,
    categoria, dificultad, highlights, servicios_incluidos, servicios_no_incluidos,
    carpeta_img, hora_inicio, activo
  ) VALUES 
  (
    'PALLAY PUNCHU',
    14, 1, 35.82, 120.0,
    'TURISMO', 'FACIL',
    '{"itinerario": "Iniciamos la experiencia con el traslado desde Cusco hacia el poblado de ***Cusipata***, donde disfrutamos de un ***desayuno tradicional***. En el camino apreciamos el ***puente colonial de Checacupe*** y un criadero de ***camélidos sudamericanos***, antes de continuar hacia el punto de inicio de la caminata en un entorno natural de gran belleza.\n\nLa caminata es ***sencilla y panorámica***, recorriendo el impresionante ***bosque de piedras*** y disfrutando de vistas de majestuosos ***nevados*** como el ***Ausangate***. Visitamos la espectacular ***Montaña Pallay Punchu***, famosa por sus ***formaciones filudas multicolores***. Finalizamos con un ***almuerzo buffet novo-andino*** y retornamos a ***Cusco***."}'::jsonb,
    '{"incluye": ["Recojo del Hotel", "Ticket de Ingreso", "Asistencia"]}'::jsonb,
    '{"no_incluye": ["Gastos extras"]}'::jsonb,
    'pallay_punchu', '08:00:00', TRUE
  ),
  (
    'CITY TOUR LIMA',
    4, 1, 23.0, 77.05,
    'CULTURA', 'FACIL',
    '{"itinerario": "Iniciamos el recorrido con una vista panorámica de la ***Huaca Pucllana***, importante ***centro ceremonial prehispánico*** que refleja la herencia ancestral de Lima. Continuamos hacia el ***Centro Histórico*** para apreciar emblemáticos monumentos coloniales como la ***Plaza Mayor***, el ***Palacio de Gobierno***, la ***Catedral*** y otros edificios que marcaron el periodo del ***Virreinato del Perú***.\n\nLa experiencia prosigue con la visita al ***Conjunto Monumental de San Francisco***, destacado por su extraordinario ***arte religioso colonial*** y las famosas ***Catacumbas***. Finalizamos explorando la ***Lima contemporánea*** en zonas residenciales como ***San Isidro***, ***Miraflores*** y el moderno ***Larcomar***, con vistas al océano Pacífico."}'::jsonb,
    '{"incluye": ["Recojo del Hotel ", "Boleto de Ingreso", "Guia Profesional", "Transporte Turistico"]}'::jsonb,
    '{"no_incluye": ["Gastos Extras", "Alimentación"]}'::jsonb,
    'city_tour_lima_colonial_y_moderna', '08:30:00', TRUE
  ),
  (
    'RECEPCION EN LIMA - CITY TOUR',
    4, 1, 30.0, 101.0,
    'CULTURA', 'FACIL',
    '{"itinerario": "A la llegada a Lima, nuestro personal recibe a los pasajeros y realiza el traslado al ***hotel seleccionado***. Posteriormente iniciamos el ***City Tour por Lima*** con una vista panorámica de la ***Huaca Pucllana***, importante ***centro ceremonial prehispánico*** que refleja el legado ancestral de la ciudad.\n\nContinuamos el recorrido por el ***Centro Histórico de Lima***, Patrimonio de la Humanidad, visitando la ***Plaza Mayor***, la ***Catedral***, el ***Palacio de Gobierno*** y otros monumentos coloniales. La experiencia incluye el ***Museo del Banco Central de Reserva***, el ***Convento de San Francisco*** con sus famosas ***Catacumbas*** y el histórico ***Monasterio de Santo Domingo***, concluyendo una jornada cultural imperdible."}'::jsonb,
    '{"incluye": ["Recojo del Aeropuerto de Lima ", "Boleto de Ingreso a todos los atractivos", "Guia Profesional", "Transporte Turistico", "Noche de Hotel en Lima Miraflores"]}'::jsonb,
    '{"no_incluye": ["Vuelo Internacional", "Alimentación"]}'::jsonb,
    'city_tour_lima_colonial_y_moderna', '08:30:00', TRUE
  );
  INSERT INTO tour (
    nombre, duracion_horas, duracion_dias, precio_adulto_extranjero, precio_adulto_nacional,
    categoria, dificultad, highlights, servicios_incluidos, servicios_no_incluidos,
    carpeta_img, hora_inicio, activo
  ) VALUES 
  (
    'TOUR GASTRONOMICO PERUANO',
    4, 1, 80.0, 268.0,
    'GASTRONOMÍA', 'FACIL',
    '{"itinerario": "Iniciamos la experiencia con la visita a un ***mercado tradicional de Cusco***, donde exploramos la ***cultura local*** y los productos que dan identidad a la reconocida ***gastronomía peruana***. Durante el recorrido descubrimos una gran variedad de ***ingredientes nativos***, aromas y sabores que forman parte de la historia culinaria de la región, considerada uno de los mejores destinos gastronómicos del mundo.\n\nLa actividad continúa con una clase práctica dirigida por un ***chef local***, quien comparte ***técnicas ancestrales***, secretos y tradiciones mientras participamos en la preparación de auténticos ***platos peruanos***. Todo se desarrolla en un ambiente diseñado para conectar con las ***raíces culturales*** y disfrutar una experiencia gastronómica única."}'::jsonb,
    '{"incluye":   ["Recojo del Hotel", "Chef de Cocina", "Manejo de Cocina y Comedor", "Almuerzo o Cena", "Visita el Mercado Local", "Clases de Cocaina"]}'::jsonb,
    '{"no_incluye": ["Gastos Extras"]}'::jsonb,
    'tour_gastronomico_peruano', '08:00:00', TRUE
  ),
  (
    'TOUR MISTICO',
    3, 1, 18.81, 63.0,
    'MÍSTICO', 'FACIL',
    '{"itinerario": "Iniciamos el recorrido desde el corazón de Cusco rumbo a la ***Morada de los Dioses***, un impresionante conjunto de ***esculturas líticas contemporáneas*** inspiradas en la ***cosmovisión andina*** y la veneración a la ***Pachamama***. Continuamos hacia el ***Valle de los Duendes***, un espacio mágico donde destacan esculturas de piedra integradas a ***formaciones naturales*** y senderos llenos de misticismo.\n\nLa experiencia prosigue en el ***Humedal de Huasao***, un importante ***pulmón verde*** con abundante flora y fauna, y finaliza en el encantador ***Bosque de los Ents***, inspirado en el universo de ***Tolkien***. Retornamos a ***Cusco*** tras una jornada llena de ***arte, naturaleza y energía espiritual***."}'::jsonb,
    '{"incluye": ["Ticket de Ingreso", "Guia Profesional", "Transporte Turistico"]}'::jsonb,
    '{"no_incluye": ["Alimentación", "Gastos Extras"]}'::jsonb,
    'tour_mistico', '08:30:00', TRUE
  ),
  (
    'DIA LIBRE',
    0, 1, 0.00, 0.00,
    'LIBRE', 'FACIL',
    '{"itinerario": "Disfrutarán de un ***día libre en la ciudad de Cusco***, ideal para recorrer a su propio ritmo sus calles llenas de ***historia y cultura***. Podrán visitar la ***Plaza de Armas***, museos, templos coloniales, barrios tradicionales y mercados artesanales, donde encontrarán textiles, souvenirs y productos locales que reflejan la ***identidad andina***.\n\nEste día es perfecto para ***explorar, descansar o realizar actividades opcionales***, degustar la ***gastronomía local*** en restaurantes típicos y cafés, y seguir adaptándose a la altura, disfrutando del ***ambiente único de la capital del Imperio Inca*** antes de continuar con el itinerario."}'::jsonb,
    '{"incluye": ["Asistencia informativa"]}'::jsonb,
    '{"no_incluye": ["Guiado", "Transporte", "Entradas", "Alimentacion"]}'::jsonb,
    'dia_libre', '00:00:00', TRUE
  ),
  (
    'DIA LIBRE - AGUAS CALIENTES',
    0, 1, 0.00, 0.00,
    'LIBRE', 'FACIL',
    '{"itinerario": "Disfrutarán de un ***día libre en Aguas Calientes*** para realizar actividades a su elección, como visitar la ***Plaza de Armas***, el ***Mariposario***, los ***Baños Termales***, el ***Museo de Sitio Manuel Chávez Ballón*** o recorrer el ***mercado artesanal***, ideal para adquirir recuerdos y artesanías locales del pueblo.\n\nPosteriormente se realizará el ***retorno a Cusco*** en tren con destino a ***Ollantaytambo***. A la llegada, nuestro transporte estará esperando para el traslado hacia la ciudad del Cusco, dejándolos cerca de la ***Plaza Mayor***, desde donde podrán dirigirse cómodamente a su hotel."}'::jsonb,
    '{"incluye": ["Traslado Hotel - Apto", "Ticket de Tren Local", "Transporte Ollanta - Cusco"]}'::jsonb,
    '{"no_incluye": ["BAños Termales", "Gastos Extras", "Alimentacion"]}'::jsonb,
    'dia_libre', '00:00:00', TRUE
  ),
  (
    'RECEPCION EN EL AEROPUERTO DE CUSCO',
    0, 1, 0.00, 0.00,
    'LOGISTICA', 'FACIL',
    '{"itinerario": "A su llegada al ***aeropuerto de Cusco***, nuestro ***personal de la agencia*** los estará esperando para brindarles una ***cálida bienvenida*** y asistirlos con el ***traslado privado hacia su hotel seleccionado***. Durante el recorrido podrán apreciar los primeros paisajes de la ***ciudad imperial***, mientras reciben recomendaciones básicas para una adecuada ***adaptación a la altura***.\n\nAl llegar al hotel, contarán con tiempo libre para ***descansar y aclimatarse***, disfrutar de las instalaciones y prepararse para iniciar las ***experiencias culturales, históricas y naturales*** que ofrece Cusco, permitiendo comenzar el viaje de manera ***cómoda, segura y organizada***."}'::jsonb,
    '{"incluye": ["Traslados APTO", "Transporte Turistico", "Hotel en el Cusco"]}'::jsonb,
    '{"no_incluye": ["Alimentación", "Gastos Extras"]}'::jsonb,
    'recepcion_aeropuerto', '00:00:00', TRUE
  ),
  (
    'RECEPCION EN EL AEROPUERTO DE LIMA',
    0, 1, 0.00, 0.00,
    'LOGISTICA', 'FACIL',
    '{"itinerario": "A su llegada a la ciudad de ***Lima***, nuestro personal estará esperándolos en el aeropuerto para brindarles una ***cálida bienvenida*** y realizar el traslado hacia su hotel seleccionado. Durante el recorrido podrán tener un primer contacto con la ***capital del Perú***, una ciudad que combina modernidad, historia y tradición.\n\nUna vez en el hotel, contarán con tiempo para ***descansar y aclimatarse*** después del viaje, preparándose para iniciar las actividades programadas. Este momento es ideal para relajarse, organizar sus pertenencias y comenzar a disfrutar del ***ambiente urbano y cultural*** que ofrece Lima antes de continuar con su itinerario."}'::jsonb,
    '{"incluye": ["Traslados APTO", "Transporte Turistico", "Hotel en el Cusco"]}'::jsonb,
    '{"no_incluye": ["Alimentación", "Gastos Extras"]}'::jsonb,
    'recepcion_aeropuerto', '00:00:00', TRUE
  ),
  (
    'RUTA AYMARA',
    10, 1, 40.00, 135.00,
    'LOGISTICA', 'FACIL',
    '{"itinerario": "Iniciaremos la experiencia con el recojo desde los ***hoteles en Puno*** para dirigirnos hacia el sur del altiplano. La primera visita será ***Chucuito***, conocida como la ***Ciudad de las Cajas Reales***, donde recorreremos su plaza principal, el ***reloj solar***, la iglesia colonial y el enigmático ***Templo de la Fertilidad Inka Uyu***. Continuaremos hacia las ***Chullpas de Molloco***, antiguas torres funerarias ***preincaicas*** de gran valor histórico.\n\nEl recorrido prosigue con la visita a los ***Waru Warus Andinos***, un impresionante ***sistema agrícola ancestral*** utilizado para el mejoramiento de cultivos. Luego conoceremos ***Aramu Muro o Wilca Uta***, la mística ***Puerta de los Dioses***, un lugar sagrado rodeado de leyendas y energía especial. Finalmente llegaremos a ***Juli***, conocida como la ***Roma de América***, con una vista privilegiada del ***Lago Titicaca***, antes de continuar hacia ***Copacabana*** para el descanso."}'::jsonb,
    '{"incluye": ["Recojo del terminal", "Transporte Turistico", "Guia Profesional", "Ingresos"]}'::jsonb,
    '{"no_incluye": ["Alimentación", "Gastos Extras"]}'::jsonb,
    'ruta_aymara', '00:00:00', TRUE
  ),
  (
    'RUTA DEL SILLAR',
    10, 1, 50.00, 168.00,
    'LOGISTICA', 'FACIL',
    '{"itinerario": "Disfrutaremos de una ***excursión de medio día*** por la tradicional ***Ruta del Sillar***, iniciando con una parada en el ***Mirador de Chilina***, desde donde se aprecian espectaculares vistas de la ciudad de Arequipa y los imponentes volcanes ***Misti, Chachani y Pichu Pichu***. Continuaremos hacia las ***Canteras de Añashuayco***, donde conoceremos el proceso artesanal de extracción y tallado del sillar, piedra emblemática de la arquitectura local.\n\nEl recorrido prosigue con una caminata por la ***Quebrada de Culebrillas***, un estrecho cañón de sillar rosado con formaciones naturales únicas y antiguos ***petroglifos Wari***. Tras finalizar la visita, retornaremos al centro de la ciudad y posteriormente se realizará el ***traslado al aeropuerto de Arequipa*** para el retorno a Lima."}'::jsonb,
    '{"incluye": ["Recojo del Hotel", "Tickets de Ingreso", "Almuerzo", "Guia Profesional", "Bote Turistico", "Botiquin de Primeros Auxilios", "Noche en casa familiar"]}'::jsonb,
    '{"no_incluye": [ "Hospedaje", "Gastos Extras"]}'::jsonb,
    'ruta_aymara', '00:00:00', TRUE
  ),
  (
    'CITY TOUR AREQUIPA(Campiña)',
    4, 1, 40.00, 135.00,
    'LOGISTICA', 'FACIL',
    '{"itinerario": "A su llegada al ***terminal terrestre de Arequipa***, nuestro personal estará esperándolo para el traslado al ***hotel seleccionado***. Posteriormente iniciaremos el recorrido por la tradicional ***Campiña Arequipeña***, una experiencia que combina naturaleza, historia y arquitectura alrededor de la ***Ciudad Blanca***. El tour comienza con el recojo desde los hoteles y un desplazamiento hacia los paisajes rurales que rodean la ciudad.\n\nDurante el recorrido visitaremos el ***Mirador de Sachaca***, desde donde se aprecia una vista privilegiada de ***Arequipa y sus volcanes***. Continuaremos hacia la ***Misión del Fundador***, una emblemática construcción colonial vinculada al origen de la ciudad. Finalmente llegaremos al ***Molino de Sabandía***, edificado en ***sillar volcánico***, donde se conserva un antiguo molino de piedra rodeado de un encantador ***entorno andino***."}'::jsonb,
    '{"incluye": ["Recojo del terminal", "Transporte Turistico", "Guia Profesional", "Ingresos"]}'::jsonb,
    '{"no_incluye": ["Alimentación", "Gastos Extras"]}'::jsonb,
    'city_tour_arequipa', '00:00:00', TRUE
  ),
  (
    'CAÑON DEL COLCA Y RESERVAS DE VICUÑAS',
    4, 1, 95.00, 320.00,
    'LOGISTICA', 'FACIL',
    '{"itinerario": "Luego del desayuno, iniciaremos el recorrido hacia el impresionante ***Mirador de la Cruz del Cóndor***, uno de los puntos más emblemáticos del ***Cañón del Colca***. Desde este lugar privilegiado se podrá apreciar la majestuosidad de uno de los cañones más profundos del mundo y observar el sobrevuelo del ***cóndor andino***, ave sagrada de los Incas, ideal para capturar fotografías inolvidables en un entorno natural único.\n\nDurante el trayecto atravesaremos pintorescos pueblos andinos como ***Pinchollo, Madrigal, Lari, Maca, Achoma y Yanque***, donde se conservan tradiciones ancestrales y paisajes rurales encantadores. Finalizada la visita, continuaremos el viaje de retorno hacia ***Puno*** en transporte turístico, llegando a la ciudad para descansar y prepararnos para las siguientes experiencias del itinerario."}'::jsonb,
    '{"incluye": ["Recojo del terminal", "Transporte Turistico", "Guia Profesional", "Ingresos"]}'::jsonb,
    '{"no_incluye": ["Alimentación", "Gastos Extras"]}'::jsonb,
    'cañon_reservas_vicuña', '00:00:00', TRUE
  ),
  (
    'CAÑON DEL COLCA CHIVAY',
    4, 1, 95.00, 320.00,
    'LOGISTICA', 'FACIL',
    '{"itinerario": "Luego del desayuno, iniciaremos el recorrido hacia el impresionante ***Mirador de la Cruz del Cóndor***, uno de los puntos más emblemáticos del ***Cañón del Colca***. Desde este lugar privilegiado se podrá apreciar la majestuosidad de uno de los cañones más profundos del mundo y observar el sobrevuelo del ***cóndor andino***, ave sagrada de los Incas, ideal para capturar fotografías inolvidables en un entorno natural único.\n\nDurante el trayecto atravesaremos pintorescos pueblos andinos como ***Pinchollo, Madrigal, Lari, Maca, Achoma y Yanque***, donde se conservan tradiciones ancestrales y paisajes rurales encantadores. Finalizada la visita, continuaremos el viaje de retorno hacia ***Puno*** en transporte turístico, llegando a la ciudad para descansar y prepararnos para las siguientes experiencias del itinerario."}'::jsonb,
    '{"incluye": ["Recojo del terminal", "Transporte Turistico", "Guia Profesional", "Ingresos"]}'::jsonb,
    '{"no_incluye": ["Alimentación", "Gastos Extras"]}'::jsonb,
    'cañon_chivay', '00:00:00', TRUE
  ),
  (
    'LAGO TITICACA(Islas Urus e Taquile)',
    4, 1, 30.00, 135.00,
    'LOGISTICA', 'FACIL',
    '{"itinerario": "Después del desayuno en el hotel, nos trasladaremos al ***puerto de Puno*** para embarcarnos en una navegación por el majestuoso ***Lago Titicaca***. Nuestra primera visita será a las ***Islas Flotantes de los Uros***, donde conoceremos de cerca su forma de vida ancestral, sus viviendas construidas con totora y su destacada ***artesanía tradicional***, en una experiencia cultural única sobre el lago navegable más alto del mundo.\n\nContinuaremos el recorrido en embarcación hacia la encantadora ***Isla de Taquile***, reconocida por su extraordinaria belleza natural y su valioso legado ***cultural, étnico y arqueológico***. Durante la visita apreciaremos sus paisajes andinos, tradiciones vivas y organización comunitaria. Finalizada la experiencia, retornaremos en barco a la ciudad de ***Puno***, concluyendo esta inolvidable jornada lacustre."}'::jsonb,
    '{"incluye": ["Recojo del Hotel", "Transporte Turistico", "Guia Profesional", "Boleto Turistico", "Almuerzo" ]}'::jsonb,
    '{"no_incluye": ["Gastos Extras"]}'::jsonb,
    'cañon_chivay', '00:00:00', TRUE
  ),
  (
    'LAGO TITICACA(Islas Urus, Amantani) Full Day',
    9, 1, 40.00, 135.00,
    'LOGISTICA', 'FACIL',
    '{"itinerario": "Después del desayuno, nos trasladaremos al ***puerto de Puno*** para iniciar una experiencia inolvidable por el ***Lago Titicaca***. La primera visita será a las ***Islas Flotantes de los Uros***, donde conoceremos cómo estas comunidades construyen y mantienen sus islas de totora, además de aprender sobre su estilo de vida ancestral en el lago navegable más alto del mundo. Tras esta visita, continuaremos la navegación rumbo a la ***Isla de Amantaní***.\n\nA la llegada, disfrutaremos de un ***almuerzo típico local*** y recibiremos una cálida bienvenida por parte de la comunidad. Las familias anfitrionas se encargarán del ***alojamiento y la convivencia cultural***. Por la tarde participaremos en una ***ceremonia andina*** de agradecimiento al universo en la montaña sagrada ***Pacha Tata***. Por la noche, compartiremos una ***cena tradicional y fiesta folclórica*** antes de pernoctar en la isla."}'::jsonb,
    '{"incluye": ["Recojo del Hotel", "Transporte Turistico", "Guia Profesional", "Boleto Turistico", "Almuerzo" ]}'::jsonb,
    '{"no_incluye": ["Gastos Extras"]}'::jsonb,
    'islas_urus_amantani', '00:00:00', TRUE
  ),
  (
    'DIA LIBRE Y SALIDA AL AEROPUERTO',
    0, 1, 0.00, 0.00,
    'LOGISTICA', 'FACIL',
    '{"itinerario": "Disfrutarán de un ***día libre en Cusco*** para explorar la ciudad a su propio ritmo, visitando la ***Plaza de Armas***, museos, mercados artesanales o recorriendo sus calles históricas. Este tiempo permite realizar compras, adquirir ***souvenirs*** y vivir el ambiente cultural que caracteriza a la antigua capital del imperio inca.\n\nA la hora indicada, realizamos el traslado al ***aeropuerto*** para abordar el vuelo de retorno hacia ***Lima***, concluyendo así una experiencia inolvidable llena de ***historia, cultura y tradición andina***."}'::jsonb,
    '{"incluye": ["Traslado al hotel -APTO", "Transporte Turistico"]}'::jsonb,
    '{"no_incluye": ["Alimentación", "Gastos Extras"]}'::jsonb,
    'dia_libre_salida', '00:00:00', TRUE
  );
  INSERT INTO proveedor (nombre_comercial, servicios_ofrecidos, contacto_telefono)
  VALUES
  ('LARRY GUIA', '{"GUIA"}', '+51 973 359 213'),
  ('JOSE CHAMPI MAPI', '{"GUIA"}', '+51 984 886 200'),
  ('ROSA GUIA LIMA', '{"GUIA"}', '+51 994 967 231'),
  ('VICKI GUIA PUNO', '{"GUIA"}', '+51 951 088 248'),
  ('VLADIMIRO LARREA', '{"GUIA"}', '+51 967 029 331'),
  ('FRANCISCO ALCANTARA', '{"TRANSPORTE"}', '+51 981 327 122'),
  ('JAIME BUS', '{"TRANSPORTE"}', '+51 990 002 244'),
  ('CENTRAL DE RESERVAS', '{"TRANSPORTE"}', '+51 933 550 685'),
  ('QORIALVA', '{"TRANSPORTE"}', '+51 939 134 062'),
  ('MARIA RENAULT', '{"TRANSPORTE"}','+51 913 477 358'),
  ('ANDEAN TREKING', '{"AGENCIA"}', '+51 980 852 691'),
  ('MIGUEL PACAY', '{"AGENCIA"}', '+51 974 446 170'),
  ('ROSA MORADA', '{"AGENCIA"}', '+51 964 668 030'),
  ('PICAFLOR', '{"AGENCIA"}', '+51 987 420 868'),
  ('FUTURISMO', '{"AGENCIA"}', '+51 984 736 982'),
  ('AERODIANA', '{"AGENCIA"}', '+51 989 046 289'),
  ('XTREME', '{"AGENCIA"}', '+51 917 916 982'),
  ('IRVIN', '{"AGENCIA"}', '+51 984 672 163'),
  ('VITU', '{"AGENCIA"}', '+51 991 956 104'),
  ('CEVICHE', '{"AGENCIA"}', '+51 956 849 794');

  -- 2.5. PAQUETES PREDEFINIDOS
  DO $$
  DECLARE
      p_id INTEGER;
      t_id INTEGER;
  BEGIN
      INSERT INTO paquete (nombre, descripcion, dias, noches, precio_sugerido, temporada, destino_principal)
      VALUES ('PERÚ PARA EL MUNDO 8D/7N', 'Recorrido completo desde la costa hasta Cusco.', 8, 7, 0.00, 'TODO EL AÑO', 'PERÚ')
      RETURNING id_paquete INTO p_id;
      
      -- Vincular tours
      SELECT id_tour INTO t_id FROM tour WHERE nombre = 'RECEPCION EN LIMA - CITY TOUR' LIMIT 1;
      INSERT INTO paquete_tour (id_paquete, id_tour, orden, dia_del_paquete) VALUES (p_id, t_id, 1, 1);
      SELECT id_tour INTO t_id FROM tour WHERE nombre = 'LIMA - ISLAS BALLESTAS - HUACACHINA' LIMIT 1;
      INSERT INTO paquete_tour (id_paquete, id_tour, orden, dia_del_paquete) VALUES (p_id, t_id, 2, 2);
      SELECT id_tour INTO t_id FROM tour WHERE nombre = 'RECEPCION - CUSCO, CITY TOUR' LIMIT 1;
      INSERT INTO paquete_tour (id_paquete, id_tour, orden, dia_del_paquete) VALUES (p_id, t_id, 3, 3);
      SELECT id_tour INTO t_id FROM tour WHERE nombre = 'VALLE VIP CONEXIÓN MACHU PICCHU' LIMIT 1;
      INSERT INTO paquete_tour (id_paquete, id_tour, orden, dia_del_paquete) VALUES (p_id, t_id, 4, 4);
      SELECT id_tour INTO t_id FROM tour WHERE nombre = 'VISITA A MACHU PICCHU' LIMIT 1;
      INSERT INTO paquete_tour (id_paquete, id_tour, orden, dia_del_paquete) VALUES (p_id, t_id, 5, 5);
      SELECT id_tour INTO t_id FROM tour WHERE nombre = 'LAGUNA HUMANTAY' LIMIT 1;
      INSERT INTO paquete_tour (id_paquete, id_tour, orden, dia_del_paquete) VALUES (p_id, t_id, 6, 6);
      SELECT id_tour INTO t_id FROM tour WHERE nombre = 'MONTAÑA DE COLORES' LIMIT 1;
      INSERT INTO paquete_tour (id_paquete, id_tour, orden, dia_del_paquete) VALUES (p_id, t_id, 7, 7);
      SELECT id_tour INTO t_id FROM tour WHERE nombre = 'DIA LIBRE Y SALIDA AL AEROPUERTO' LIMIT 1;
      INSERT INTO paquete_tour (id_paquete, id_tour, orden, dia_del_paquete) VALUES (p_id, t_id, 8, 8);
  END $$;

  DO $$
  DECLARE
      p_id INTEGER;
      t_id INTEGER;
  BEGIN
      INSERT INTO paquete (nombre, descripcion, dias, noches, precio_sugerido, temporada, destino_principal)
      VALUES ('CUSCO TRADICIONAL 5D/4N', 'Lo esencial: Arqueología, Valles y Machu Picchu.', 5, 4, 0.00, 'TODO EL AÑO', 'CUSCO')
      RETURNING id_paquete INTO p_id;

      SELECT id_tour INTO t_id FROM tour WHERE nombre = 'RECEPCION - CUSCO, CITY TOUR' LIMIT 1;
      INSERT INTO paquete_tour (id_paquete, id_tour, orden, dia_del_paquete) VALUES (p_id, t_id, 1, 1);
      SELECT id_tour INTO t_id FROM tour WHERE nombre = 'VALLE VIP CONEXIÓN MACHU PICCHU' LIMIT 1;
      INSERT INTO paquete_tour (id_paquete, id_tour, orden, dia_del_paquete) VALUES (p_id, t_id, 2, 2);
      SELECT id_tour INTO t_id FROM tour WHERE nombre = 'VISITA A MACHU PICCHU' LIMIT 1;
      INSERT INTO paquete_tour (id_paquete, id_tour, orden, dia_del_paquete) VALUES (p_id, t_id, 3, 3);
      SELECT id_tour INTO t_id FROM tour WHERE nombre = 'MONTAÑA DE COLORES' LIMIT 1;
      INSERT INTO paquete_tour (id_paquete, id_tour, orden, dia_del_paquete) VALUES (p_id, t_id, 4, 4);
      SELECT id_tour INTO t_id FROM tour WHERE nombre = 'DIA LIBRE Y SALIDA AL AEROPUERTO' LIMIT 1;
      INSERT INTO paquete_tour (id_paquete, id_tour, orden, dia_del_paquete) VALUES (p_id, t_id, 5, 5);
  END $$;

  -- ==============================================================
  -- SECCIÓN 2.2: PROVEEDORES POR DEFECTO
  -- ==============================================================
  INSERT INTO proveedor (nombre_comercial, servicios_ofrecidos, contacto_telefono, pais)
  VALUES 
  ('OPERACION PROPIA', ARRAY['GUIA', 'TRANSPORTE', 'ALIMENTACION', 'ALOJAMIENTO', 'TICKETS', 'ENDOSE'], '---', 'Perú'),
  ('PERURAIL', ARRAY['TICKETS', 'TRANSPORTE'], '---', 'Perú'),
  ('INCARAIL', ARRAY['TICKETS', 'TRANSPORTE'], '---', 'Perú'),
  ('ENTRADAS MACHU PICCHU', ARRAY['TICKETS'], '---', 'Perú'),
  ('CONSETTUR', ARRAY['TICKETS', 'TRANSPORTE'], '---', 'Perú');

  -- ==============================================================
  -- SECCIÓN 3: FUNCIONES Y TRIGGERS (AUTOMATIZACIÓN)
  -- ==============================================================

  -- 3.1. Actualizar updated_at
  CREATE OR REPLACE FUNCTION update_updated_at_column()
  RETURNS TRIGGER AS $$
  BEGIN
      NEW.updated_at = CURRENT_TIMESTAMP;
      RETURN NEW;
  END;
  $$ language 'plpgsql';

  CREATE TRIGGER update_venta_updated_at BEFORE UPDATE ON venta
      FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

  -- 3.2. Sincronizar costo_total
  CREATE OR REPLACE FUNCTION sync_costo_venta_total()
  RETURNS TRIGGER AS $$
  DECLARE
      v_moneda_v VARCHAR(10);
      v_tc DECIMAL(8,4);
      v_id_venta INTEGER;
  BEGIN
      v_id_venta := COALESCE(NEW.id_venta, OLD.id_venta);
      SELECT moneda, tipo_cambio INTO v_moneda_v, v_tc FROM venta WHERE id_venta = v_id_venta;
      IF v_tc IS NULL OR v_tc = 0 THEN v_tc := 1; END IF;

      -- Actualizar Venta: Normalizar Costo Total a la moneda de la venta
      UPDATE venta SET 
          costo_total = (
              SELECT COALESCE(SUM(
                  CASE 
                      WHEN s.moneda = v_moneda_v THEN (s.costo_unitario * s.cantidad_pax)
                      WHEN v_moneda_v = 'USD' AND s.moneda = 'PEN' THEN (s.costo_unitario * s.cantidad_pax) / v_tc
                      WHEN v_moneda_v = 'PEN' AND s.moneda = 'USD' THEN (s.costo_unitario * s.cantidad_pax) * v_tc
                      ELSE (s.costo_unitario * s.cantidad_pax)
                  END
              ), 0)
              FROM venta_servicio_proveedor s
              WHERE s.id_venta = v_id_venta
          )
      WHERE id_venta = v_id_venta;
      
      RETURN NULL;
  END;
  $$ language 'plpgsql';

  CREATE TRIGGER trigger_sync_costo AFTER INSERT OR UPDATE OR DELETE ON venta_servicio_proveedor
      FOR EACH ROW EXECUTE FUNCTION sync_costo_venta_total();

  -- 3.3. Calcular utilidad
  CREATE OR REPLACE FUNCTION calcular_utilidad_venta()
  RETURNS TRIGGER AS $$
  BEGIN
      NEW.utilidad_bruta = COALESCE(NEW.precio_total_cierre, 0) - COALESCE(NEW.costo_total, 0);
      RETURN NEW;
  END;
  $$ language 'plpgsql';

  CREATE TRIGGER trigger_calc_utilidad BEFORE INSERT OR UPDATE OF precio_total_cierre, costo_total ON venta
      FOR EACH ROW EXECUTE FUNCTION calcular_utilidad_venta();

  -- 3.4. Sincronizar estado_pago de la venta (Basado en tabla Pagos)
  CREATE OR REPLACE FUNCTION sync_estado_pago_venta()
  RETURNS TRIGGER AS $$
  DECLARE
      total_deuda DECIMAL(10,2);
      total_pagado DECIMAL(10,2);
      nuevo_estado VARCHAR(50);
  BEGIN
      -- Obtener el precio total de la venta
      SELECT precio_total_cierre INTO total_deuda FROM venta WHERE id_venta = COALESCE(NEW.id_venta, OLD.id_venta);
      
      -- Sumar todos los pagos (reembolsos restan)
      SELECT COALESCE(SUM(CASE WHEN tipo_pago = 'REEMBOLSO' THEN -monto_pagado ELSE monto_pagado END), 0) 
      INTO total_pagado 
      FROM pago 
      WHERE id_venta = COALESCE(NEW.id_venta, OLD.id_venta);

      -- Determinar estado
      IF total_pagado <= 0 THEN
          nuevo_estado := 'PENDIENTE';
      ELSIF total_pagado < total_deuda THEN
          nuevo_estado := 'PARCIAL';
      ELSE
          nuevo_estado := 'COMPLETADO';
      END IF;

      -- Actualizar venta
      UPDATE venta SET estado_pago = nuevo_estado WHERE id_venta = COALESCE(NEW.id_venta, OLD.id_venta);
      
      RETURN NULL;
  END;
  $$ language 'plpgsql';

  CREATE TRIGGER trigger_sync_estado_pago AFTER INSERT OR UPDATE OR DELETE ON pago
      FOR EACH ROW EXECUTE FUNCTION sync_estado_pago_venta();


  -- ==============================================================
  -- SECCIÓN 5: SEGURIDAD (RLS Y POLÍTICAS)
  -- ==============================================================

  -- Habilitar RLS
  ALTER TABLE usuarios_app ENABLE ROW LEVEL SECURITY;
  ALTER TABLE vendedor ENABLE ROW LEVEL SECURITY;
  ALTER TABLE venta ENABLE ROW LEVEL SECURITY;
  -- (Opcional: aplicar a todas las demás tablas)

  -- Políticas permisivas (MODO DESARROLLO)
  DO $$ 
  DECLARE tabla_nombre text;
  BEGIN
      FOR tabla_nombre IN SELECT tablename FROM pg_tables WHERE schemaname = 'public' LOOP
          EXECUTE format('DROP POLICY IF EXISTS "Acceso total" ON %I;', tabla_nombre);
          EXECUTE format('CREATE POLICY "Acceso total" ON %I FOR ALL USING (true) WITH CHECK (true);', tabla_nombre);
      END LOOP;
  END $$;

  -- Permisos storage (Ejecutar en panel SQL)
  -- Requiere buckets 'itinerarios' y 'vouchers' creados como Públicos
  DROP POLICY IF EXISTS "Acceso Público Itinerarios" ON storage.objects;
  DROP POLICY IF EXISTS "Subida Libre Itinerarios" ON storage.objects;
  DROP POLICY IF EXISTS "Acceso Público Vouchers" ON storage.objects;
  DROP POLICY IF EXISTS "Subida Libre Vouchers" ON storage.objects;

  CREATE POLICY "Acceso Público Itinerarios" ON storage.objects FOR SELECT USING (bucket_id = 'itinerarios');
  CREATE POLICY "Subida Libre Itinerarios" ON storage.objects FOR INSERT WITH CHECK (bucket_id = 'itinerarios');
  CREATE POLICY "Acceso Público Vouchers" ON storage.objects FOR SELECT USING (bucket_id = 'vouchers');
  CREATE POLICY "Subida Libre Vouchers" ON storage.objects FOR INSERT WITH CHECK (bucket_id = 'vouchers');

  -- ==============================================================
  -- ✅ FIN DEL SCRIPT: INSTALACIÓN EXITOSA
  -- ==============================================================