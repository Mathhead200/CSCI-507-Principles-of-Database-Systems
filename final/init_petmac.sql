CREATE DATABASE petmac CHARACTER SET utf8mb4;

CREATE USER 'petmac_app'@'%' IDENTIFIED BY 'K2EDhXXv3GfnRdkd5f7A';
GRANT INSERT, SELECT, UPDATE, DELETE ON petmac.* TO 'petmac_app'@'%';

USE petmac;

CREATE TABLE product (
	sku VARCHAR(32) PRIMARY KEY,  -- PetMAC specific SKU
	upc CHAR(12),                 -- UPC-A format (12 digit) US barcode
	ean CHAR(13),                 -- EAN-13 format (13 digit) International barcode
	name varchar(100),
	
	price DECIMAL(8,2),           -- Max price $999,999.99 USD
	in_stock INT,                 -- Quantity in stock
	
	notes TEXT,
	last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE customer (
	id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
	first_name VARCHAR(100),
	last_name VARCHAR(100),
	email VARCHAR(254),      -- Max length for email address per RFC 5321
	phone VARCHAR(15),       -- per E.164 internation phone numner spec. (digits only)

	birthday DATE,           -- For deals and marketing
	
	notes TEXT,
	last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

	UNIQUE (first_name, last_name, email)  -- It would be confusing to have two distinct customers with the same full name and email
);

CREATE TABLE distributor (
	id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
	name VARCHAR(100),
	
	url VARCHAR(2083),   -- Conventionally used historical maximum URL length per Internet Explorer
	
	notes TEXT,
	last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

CREATE TABLE pet (
	id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
	name VARCHAR(100),

	type VARCHAR(16),
	breed VARCHAR(100),
	birthday DATE,

	favorites TEXT,
	food_allergies TEXT,
	medical TEXT,

	notes TEXT,
	last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
);

-- "Receipts" refer to customer purchases (or returns)
CREATE TABLE receipt (
	id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
	
	customer_id INT UNSIGNED NOT NULL,
	`date` TIMESTAMP,         -- date of purchase
	sub_total DECIMAL(8, 2),  -- may include both purchances and returns
	tax DECIMAL(8, 2),
	discounts DECIMAL(8, 2),
	total DECIMAL(8, 2),

	notes TEXT,
	last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

	FOREIGN KEY (customer_id) REFERENCES customer(id) ON UPDATE CASCADE
);

-- "Orders" refer to shipments/manifests from distributors for restocking inventory (or returns to distributors / credits)
CREATE TABLE `order` (
	id INT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
	
	distributor_id INT UNSIGNED NOT NULL,
	`date` TIMESTAMP,
	sub_total DECIMAL(8, 2),  -- may include both purchances and returns/credits
	tax DECIMAL(8, 2),
	discounts DECIMAL(8, 2),
	total DECIMAL(8, 2),

	notes TEXT,
	last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

	FOREIGN KEY (distributor_id) REFERENCES distributor(id) ON UPDATE CASCADE
);

CREATE TABLE receipt_line_item (
	id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
	receipt_id INT UNSIGNED NOT NULL,  -- which receipt does this line item belongs to

	product_sku VARCHAR(32) NOT NULL,  -- sku of purchansed product
	quantity INT UNSIGNED,             -- how many (positive for purchases; negative for returns)

	FOREIGN KEY (receipt_id) REFERENCES receipt(id) ON UPDATE CASCADE,
	FOREIGN KEY (product_sku) REFERENCES product(sku) ON UPDATE CASCADE
);

CREATE TABLE order_line_item (
	id BIGINT UNSIGNED AUTO_INCREMENT PRIMARY KEY,
	order_id INT UNSIGNED NOT NULL,

	product_sku VARCHAR(32) NOT NULL,  -- which product was ordered
	quantity INT UNSIGNED,             -- how many (positive for orders; negative for returns/credits)

	FOREIGN KEY (order_id) REFERENCES `order`(id) ON UPDATE CASCADE,
	FOREIGN KEY (product_sku) REFERENCES product(sku) ON UPDATE CASCADE
);

-- Many-to-many relation between TABLE customer and TABLE pet
CREATE TABLE pet_owner (
	customer_id INT UNSIGNED NOT NULL,  -- i.e., owner, etc.
	pet_id INT UNSIGNED NOT NULL,

	PRIMARY KEY (customer_id, pet_id),
	FOREIGN KEY (customer_id) REFERENCES customer(id) ON UPDATE CASCADE,
	FOREIGN KEY (pet_id) REFERENCES pet(id) ON UPDATE CASCADE
);
