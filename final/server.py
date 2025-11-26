from flask import Flask, request, render_template, render_template_string, jsonify, abort, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData, Table, insert, select, update, delete, and_
from sqlalchemy.orm import Session
from werkzeug.exceptions import HTTPException
import random
from datetime import datetime, timedelta

# Credentials for database connection including App user account
MYSQL_HOST = "localhost"
MYSQL_APP_USERNAME = "petmac_app"
MYSQL_APP_PASSWORD = 'K2EDhXXv3GfnRdkd5f7A'

# Set up Flask and SQLAlchemy
app = Flask("PetMAC Inventory Server", template_folder=".", static_folder="www")
app.config["SQLALCHEMY_DATABASE_URI"] = f"mysql+pymysql://{MYSQL_APP_USERNAME}:{MYSQL_APP_PASSWORD}@{MYSQL_HOST}/petmac"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Tables in database
md = MetaData()
with app.app_context():
	product = Table("product", md, autoload_with=db.engine)
	customer = Table("customer", md, autoload_with=db.engine)
	pet = Table("pet", md, autoload_with=db.engine)
	distributor = Table("distributor", md, autoload_with=db.engine)
	pet_owner = Table("pet_owner", md, autoload_with=db.engine)
	receipt = Table("receipt", md, autoload_with=db.engine)
	order = Table("order", md, autoload_with=db.engine)
	receipt_line_item = Table("receipt_line_item", md, autoload_with=db.engine)
	order_line_item = Table("order_line_item", md, autoload_with=db.engine)

	accessible_tables = [product, customer, distributor, pet, receipt, order]
	accessible_tables = { table.name : table for table in accessible_tables }

# ----- Routes ----------------------------------------------------------------
# helper functions
def denormalize_for_ui(d: dict):
	# Client should see SQL null values (None in python) represented as empty strings ("")
	return { k: (v if v is not None else "") for k, v in d.items() }

def normalize_for_sql(d: dict):
	# empty strings ("") from the client should be treated as null values (None in python)
	return { k: (v if v != "" else None) for k, v in d.items() }

def validate_table_name(table_name):
	if table_name not in accessible_tables:
		abort(404, description="TABLE not found: " + table_name)  # internally raises exception and ends function
	return accessible_tables[table_name]

# simple table views (no joins)
@app.route("/table/<table_name>/<mode>")
@app.route("/table/<table_name>/")
def render_table(table_name, mode=None):
	table = validate_table_name(table_name)
	if mode is None:
		return redirect(f"/table/{table_name}/view")
	if mode not in ["view", "edit"]:
		abort(404, description="mode not recognized: " + mode)  # internally raises exception and ends function

	pk = ",".join(col.name for col in table.primary_key.columns)
	with db.engine.connect() as conn:
		selection = conn.execute(select(table))
		th = selection.keys()
		td = [denormalize_for_ui(record._mapping) for record in selection]  # denormalize all records
		return render_template("table.j2", table=table_name, mode=mode, pk=pk, cols=len(th), th=th, td=td)

@app.route("/update/<table_name>", methods=["POST"])
def update_table(table_name):
	table = validate_table_name(table_name)
	json = request.get_json()  # list of updates, inserts, and deletes

	statements = []
	for obj in json["deletes"]:
		predicate = and_(*( table.c[pk_name] == pk_val for pk_name, pk_val in obj["pk"].items() ))
		statements.append(delete(table).where(predicate))
	for obj in json["updates"]:
		predicate = and_(*( table.c[pk_name] == pk_val for pk_name, pk_val in obj["pk"].items() ))
		statements.append(update(table).values(**normalize_for_sql(obj["values"])).where(predicate))
	for obj in json["inserts"]:
		statements.append(insert(table).values(**normalize_for_sql(obj["values"])))
	
	# execute
	rowcount = 0
	log = []
	with Session(db.engine) as session:  # batch all requested updates, inserts, and delets as a single SQL transaction
		for stmt in statements:
			result = session.execute(stmt)
			rowcount += result.rowcount
			log.append({ 'sql': str(stmt), 'rowcount': result.rowcount })
		session.commit()
	return jsonify(success=True, rowcount=rowcount, log=log)  # for logging

@app.route("/import/<table_name>", methods=["GET", "POST"])
def import_table(table_name):
	table = validate_table_name(table_name)
	if request.method == "POST":
		json = request.get_json()
		rowcount = 0
		log = []
		with Session(db.engine) as session:
			for obj in json:
				stmt = insert(table).values(**obj)
				result = session.execute(stmt)
				rowcount += result.rowcount
				log.append({ "sql": str(stmt), "rowcount": result.rowcount })
			session.commit()
		return jsonify(success=True, rowcount=rowcount, log=log)  # for logging
	else:  # GET
		return render_template("import.j2", table=table_name)

# specialized views involving joins
@app.route("/receipts")
def view_receipts():
	cid = request.args.get("cid", default="")
	dstart = request.args.get("dstart", default="")
	dend = request.args.get("dend", default="")

	with db.engine.connect() as conn:
		c_selection = conn.execute(select(customer.c.id, customer.c.first_name, customer.c.last_name))

	if cid != "":
		# Get all receipts for the selected customer
		stmt = select(receipt).where(receipt.c.customer_id == cid)
		if dstart != "":  stmt = stmt.where(receipt.c.date > dstart)
		if dend != "":    stmt = stmt.where(receipt.c.date < dend)
		with db.engine.connect() as conn:
			r_selection = conn.execute(stmt)
			cust = conn.execute(select(customer.c.first_name, customer.c.last_name).where(customer.c.id == cid)).first()._mapping
		title = f"{cust['first_name']} {cust['last_name']}"

	else:
		# Get receipts in the specified date range
		title="History"
		now = datetime.now()
		fmt = "%Y-%m-%d %H:%M:%S"  # expected format for SQL TIMESTAMP type: YYYY-MM-DD HH:MM:SS
		if dstart == "":
			yesterday = now - timedelta(days=1)
			dstart = datetime(yesterday.year, yesterday.month, yesterday.day, 0, 0, 0).strftime(fmt)
		if dend == "":
			dend = now.strftime(fmt)
		with db.engine.connect() as conn:
			print("dstart", dstart)
			print("dend", dend)
			r_selection = conn.execute(select(receipt).where(receipt.c.date.between(dstart, dend)))
	
	return render_template("receipts.j2", title=title, receipt_schema=r_selection.keys(), receipts=r_selection, customers=c_selection)

@app.route("/receipts/<receipt_id>")
def view_recipt(receipt_id):
	return render_template_string("TODO: implement")  # TODO: stub

# dev tools for testing or demos
@app.route("/dev/random/customer")
def random_customers():
	n = int(request.args.get("n", default=100))               # number of customers  to generate
	bd_p = float(request.args.get("bd_p", default=0.90))       # birth day percentage
	bd_min = float(request.args.get("bd_min", default=20))    # min age in years
	bd_max = float(request.args.get("bd_max", default=100))   # max age in years
	bd_mu = float(request.args.get("bd_mu", default=39))      # mean customer age in years
	bd_sig = float(request.args.get("bd_sig", default=22))    # standard deviation of age (in years)

	# sources: https://www.ssa.gov/oact/babynames/decades/century.html
	#          https://www.thoughtco.com/most-common-us-surnames-1422656
	# retrieved on Nov 25, 2025
	first_names = [
		# Male Names
		"James","Michael","John","Robert","David","William","Richard","Joseph","Thomas","Christopher",
		"Charles","Daniel","Matthew","Anthony","Mark","Steven","Donald","Andrew","Joshua","Paul",
		"Kenneth","Kevin","Brian","Timothy","Ronald","Jason","George","Edward","Jeffrey","Ryan",
		"Jacob","Nicholas","Gary","Eric","Jonathan","Stephen","Larry","Justin","Benjamin","Scott",
		"Brandon","Samuel","Gregory","Alexander","Patrick","Frank","Jack","Raymond","Dennis","Tyler",
		"Aaron","Jerry","Jose","Nathan","Adam","Henry","Zachary","Douglas","Peter","Noah",
		"Kyle","Ethan","Christian","Jeremy","Keith","Austin","Sean","Roger","Terry","Walter",
		"Dylan","Gerald","Carl","Jordan","Bryan","Gabriel","Jesse","Harold","Lawrence","Logan",
		"Arthur","Bruce","Billy","Elijah","Joe","Alan","Juan","Liam","Willie","Mason",
		"Albert","Randy","Wayne","Vincent","Lucas","Caleb","Luke","Bobby","Isaac","Bradley",
		
		# Female Names
		"Mary","Patricia","Jennifer","Linda","Elizabeth","Barbara","Susan","Jessica","Karen","Sarah",
		"Lisa","Nancy","Sandra","Ashley","Emily","Kimberly","Betty","Margaret","Donna","Michelle",
		"Carol","Amanda","Melissa","Deborah","Stephanie","Rebecca","Sharon","Laura","Cynthia","Amy",
		"Kathleen","Angela","Dorothy","Shirley","Emma","Brenda","Nicole","Pamela","Samantha","Anna",
		"Katherine","Christine","Debra","Rachel","Olivia","Carolyn","Maria","Janet","Heather","Diane",
		"Catherine","Julie","Victoria","Helen","Joyce","Lauren","Kelly","Christina","Joan","Judith",
		"Ruth","Hannah","Evelyn","Andrea","Virginia","Megan","Cheryl","Jacqueline","Madison","Sophia",
		"Abigail","Teresa","Isabella","Sara","Janice","Martha","Gloria","Kathryn","Ann","Charlotte",
		"Judy","Amber","Julia","Grace","Denise","Danielle","Natalie","Alice","Marilyn","Diana",
		"Beverly","Jean","Brittany","Theresa","Frances","Kayla","Alexis","Tiffany","Lori","Kathy"
	]
	last_names = [
		"Smith","Johnson","Williams","Brown","Jones","Garcia","Miller","Davis","Rodriguez","Martinez",
		"Hernandez","Lopez","Gonzales","Wilson","Anderson","Thomas","Taylor","Moore","Jackson","Martin",
		"Lee","Perez","Thompson","White","Harris","Sanchez","Clark","Ramirez","Lewis","Robinson",
		"Walker","Young","Allen","King","Wright","Scott","Torres","Nguyen","Hill","Flores",
		"Green","Adams","Nelson","Baker","Hall","Rivera","Campbell","Mitchell","Carter","Roberts",
		"Gomez","Phillips","Evans","Turner","Diaz","Parker","Cruz","Edwards","Collins","Reyes",
		"Stewart","Morris","Morales","Murphy","Cook","Rogers","Gutierrez","Ortiz","Morgan","Cooper",
		"Peterson","Bailey","Reed","Kelly","Howard","Ramos","Kim","Cox","Ward","Richardson",
		"Watson","Brooks","Chavez","Wood","James","Bennet","Gray","Mendoza","Ruiz","Hughes",
		"Price","Alvarez","Castillo","Sanders","Patel","Myers","Long","Ross","Foster","Jimenez"
	]
	us_area_codes = [
		"201","202","203","205","206","207","208","209","210","212","213","214","215","216","217","218","219",
		"220","223","224","225","227","228","229","231","234","239","240","248","251","252","253","254","256",
		"260","262","267","269","270","272","274","276","279","281","283","301","302","303","304","305","307",
		"308","309","310","312","313","314","315","316","317","318","319","320","321","323","325","327","330",
		"331","332","334","336","337","339","341","346","347","351","352","360","361","364","369","380","385",
		"386","401","402","404","405","406","407","408","409","410","412","413","414","415","417","419","423",
		"424","425","430","432","434","435","440","442","443","447","448","458","463","464","469","470","472",
		"475","478","479","480","484","501","502","503","504","505","507","508","509","510","512","513","515",
		"516","517","518","520","530","531","534","539","540","541","551","557","559","561","562","563","564",
		"567","570","571","572","573","574","575","580","582","585","586","601","602","603","605","606","607",
		"608","609","610","612","614","615","616","617","618","619","620","623","626","628","629","630","631",
		"636","641","646","650","651","657","659","660","661","662","667","669","678","680","681","682","689",
		"701","702","703","704","706","707","708","712","713","714","715","716","717","718","719","720","721",
		"724","725","726","727","730","731","732","734","737","740","743","747","754","757","760","762","763",
		"764","765","769","770","771","772","773","774","775","779","781","785","786","801","802","803","804",
		"805","806","808","810","812","813","814","815","816","817","818","820","828","830","831","832","835",
		"838","839","840","843","845","847","848","850","854","856","857","858","859","860","862","863","864",
		"865","870","872","878","901","903","904","906","907","908","909","910","912","913","914","915","916",
		"917","918","919","920","925","927","928","929","930","931","934","936","937","938","940","941","943",
		"945","947","949","951","952","954","956","959","970","971","972","973","975","978","979","980","984",
		"985","986","989","301","671","684","787","939"
	]

	customer_data = []
	for i in range(n):
		fname = random.choice(first_names)
		lname = random.choice(last_names)
		email = f"{fname}.{lname}.{i+1}@example.com"
		_area = random.choice(us_area_codes)
		_dig = random.randrange(1000)
		phone = f"{_area}-555-{_dig:04d}"
		_age = int(365.25 * max(bd_min, min(bd_max, random.gauss(bd_mu, bd_sig))))
		bday = (datetime.today() - timedelta(days=_age)).strftime("%Y-%m-%d") if random.random() < bd_p else None
		customer_data.append({
			"first_name": fname,
			"last_name": lname,
			"email": email,
			"phone": phone,
			"birthday": bday
		})
	return jsonify(customer_data)

@app.route("/dev/random/pet")
def random_pets():
	n = int(request.args.get("n", default=100))  # number of pet to generate

	# source: https://www.bluecross.org.uk/sites/default/files/d8/downloads/Blue-Cross-top-100-pet-dog-names.pdf
	#         https://www.bluecross.org.uk/sites/default/files/d8/downloads/Blue-Cross-top-100-pet-cat-names.pdf
	#         https://www.chewy.com/education/dog-breeds
	#         https://cats.com/cat-breeds
	# retrieved on Nov 25, 2025
	dog_names = [
		"Max","Charlie","Bella","Poppy","Daisy","Buster","Alfie","Millie","Molly","Rosie",
		"Buddy","Barney","Lola","Roxy","Ruby","Tilly","Bailey","Marley","Tia","Bonnie",
		"Toby","Milo","Archie","Holly","Lucy","Lexi","Bruno","Rocky","Sasha","Billy",
		"Gerbil","Bear","LUNA","Oscar","Jack","Lady","Willow","Tyson","Benji","Jake",
		"Jess","Teddy","Coco","Murphy","Sky","Honey","Lilly","Lily","Monty","Patch",
		"Rolo","Harry","Maisy","Pippa","Trixie","Bruce","Dexter","Freddie","Jasper",
		"Shadow","Milly","Missy","Pepper","Rex","Sally","Zeus","Bobby","Harvey","Lucky",
		"Ollie","Pip","Sam","Storm","Amber","Belle","Cooper","Fudge","Meg","Minnie",
		"Ozzy","Ralph","Tess","Dave","Diesel","George","Jessie","Leo","Lottie","Louie",
		"Prince","Reggie","Simba","Skye","Basil","Betsy","Chase","Dolly","Frankie","Lulu","Maggie"
	]
	cat_names = [
		"Poppy","Bella","Misty","Charlie","Molly","Smudge","Daisy","Oscar","Tilly","Milo",
		"Tigger","George","LUNA","Alfie","Felix","Lily","Rosie","Lilly","Millie","Tiger",
		"Willow","Coco","Gizmo","Betty","Jasper","Max","Simba","Smokey","Sox","Fluffy",
		"Missy","Oreo","Sophie","Belle","Cookie","Cleo","Lucy","Pebbles","Pepper","Harry",
		"Lola","Mia","Patch","Ruby","Sooty","Bob","Casper","Jess","Ziggy","Angel",
		"Bailey","Fred","Holly","Maisie","Billy","Bonnie","Freddie","Princess","Tabitha","Tinkerbell",
		"Tommy","Bobby","Fifi","Fudge","Milly","Oliver","Snowy","Tia","Tom","Annie",
		"Bertie","Brian","Flo","Jerry","Kitty","Maisy","Meg","Nala","Phoebe","Shadow",
		"Teddy","Evie","Florence","Minnie","OLLIE","Polly","Pumpkin","Toby","Barney","Boo",
		"Bubbles","Chloe","Garfield","Ginger","Ginny","Henry","Izzy","Joey","Nemo","Rio"
	]
	dog_breeds = [
		"Affenpinscher","Afghan Hound","Airedale Terrier","Akita","Alaskan Malamute",
		"American Bulldog","American Eskimo Dog","American Foxhound","American Pit Bull Terrier","American Staffordshire Terrier",
		"Anatolian Shepherd","Aussiedoodle","Australian Cattle Dog","Australian Kelpie","Australian Shepherd",
		"Australian Terrier","Barbet","Basenji","Basset Hound","Beagle",
		"Bearded Collie","Beauceron","Bedlington Terrier","Belgian Malinois","Belgian Sheepdog (Groenendael)",
		"Bernedoodle","Bernese Mountain Dog","Bichon Frise","Biewer Terrier","Bloodhound",
		"Bluetick Coonhound","Boerboel","Bolognese","Border Collie","Border Terrier",
		"Borzoi","Boston Terrier","Bouvier des Flandres","Boxer","Boykin Spaniel",
		"Briard","Brittany","Brussels Griffon","Bull Terrier","Bulldog (English Bulldog)",
		"Bullmastiff","Cairn Terrier","Cane Corso","Cardigan Welsh Corgi","Catahoula Leopard Dog",
		"Cavalier King Charles Spaniel","Cavapoo","Chesapeake Bay Retriever","Chihuahua","Chinese Crested",
		"Chinese Shar-Pei","Chinook","Chiweenie","Chow Chow","Clumber Spaniel",
		"Cockapoo","Cocker Spaniel","Collie","Coton de Tulear","Dachshund",
		"Dalmatian","Doberman Pinscher","Dogo Argentino","Dogue de Bordeaux","Dutch Shepherd",
		"English Cocker Spaniel","English Setter","English Springer Spaniel","Entlebucher Mountain Dog","Flat-Coated Retriever",
		"French Bulldog","German Pinscher","German Shepherd","German Shorthaired Pointer","German Wirehaired Pointer",
		"Giant Schnauzer","Golden Retriever","Goldendoodle","Gordon Setter","Great Dane",
		"Great Pyrenees","Greater Swiss Mountain Dog","Greyhound","Harrier","Havanese",
		"Irish Setter","Irish Terrier","Irish Water Spaniel","Irish Wolfhound","Italian Greyhound",
		"Jack Russell Terrier","Japanese Chin","Keeshond","Kerry Blue Terrier","Komondor",
		"Kuvasz","Labradoodle","Labrador Retriever","Lagotto Romagnolo","Lakeland Terrier",
		"Lancashire Heeler","Leonberger","Lhasa Apso","Maltese","Maltipoo",
		"Manchester Terrier","Mastiff","Miniature American Shepherd","Miniature Pinscher","Miniature Poodle",
		"Miniature Schnauzer","Morkie","Neapolitan Mastiff","Nederlandse Kooikerhondje","Newfoundland",
		"Norfolk Terrier","Norwegian Elkhound","Norwich Terrier","Nova Scotia Duck Tolling Retriever","Old English Sheepdog",
		"Papillon","Pekingese","Pembroke Welsh Corgi","Pharaoh Hound","Plott Hound",
		"Pointer","Pomeranian","Pomsky","Portuguese Water Dog","Pug",
		"Puggle","Puli","Pumi","Rat Terrier","Redbone Coonhound",
		"Rhodesian Ridgeback","Rottweiler","Saint Bernard","Saluki","Samoyed",
		"Schipperke","Scottish Terrier","Sheepadoodle","Shetland Sheepdog","Shiba Inu",
		"Shih Tzu","Siberian Husky","Silky Terrier","Smooth Fox Terrier","Spanish Water Dog",
		"Staffordshire Bull Terrier","Standard Poodle","Standard Schnauzer","Swedish Vallhund","Tibetan Mastiff",
		"Tibetan Spaniel","Tibetan Terrier","Toy Poodle","Treeing Walker Coonhound","Vizsla",
		"Weimaraner","Welsh Springer Spaniel","Welsh Terrier","West Highland White Terrier","Whippet",
		"Xoloitzcuintli","Yorkshire Terrier"
	]
	cat_breeds = [
		"Abyssinian","Aegean","American Bobtail","American Curl","American Longhair",
		"American Polydactyl","American Shorthair","American Wirehair","Asian Semi-Longhair","Australian Mist",
		"Balinese","Bengal","Birman","Bombay","Brazilian Shorthair",
		"British Longhair","British Shorthair","Burmese","Burmilla","California Spangled Cat",
		"Chantilly / Tiffany","Chartreux","Chausie","Cheetoh","Colorpoint Shorthair",
		"Cornish Rex","Cymric","Devon Rex","Donskoy","Dragon Li",
		"Egyptian Mau","European Shorthair","Exotic Shorthair","German Rex","Havana Brown",
		"Himalayan","Japanese Bobtail","Javanese","Korat","Kurilian Bobtail",
		"LaPerm","Maine Coon","Manx","Minuet (Napoleon)","Munchkin",
		"Nebelung","Norwegian Forest","Ocicat","Ojos Azules","Oregon Rex",
		"Oriental Bicolor","Oriental Longhair","Oriental Shorthair","Persian","Peterbald",
		"Pixie-Bob","Ragamuffin","Ragdoll","Russian Blue","Russian White, Black, and Tabby",
		"Savannah","Scottish Fold","Selkirk Rex","Serengeti","Siamese",
		"Siberian","Singapura","Snowshoe","Sokoke","Somali",
		"Sphynx","Thai Cat (Old-Style Siamese)",
		"Tonkinese","Toyger","Turkish Angora","Turkish Van","Turkish Vankedisi",
		"Ukrainian Levkoy","Ussuri","York Chocolate"
	]

	pet_data = []
	for i in range(n):
		if random.random() < 0.50:
			type = "Dog"
			name = random.choice(dog_names)
			breed = random.choice(dog_breeds)
			_age = int(365.25 * max(0, random.gauss(11.5, 2.5)))
		else:
			type = "Cat"
			name = random.choice(cat_names)
			breed = random.choice(cat_breeds)
			_age = int(365.25 * max(0, random.gauss(14, 2.5)))
		bday = (datetime.today() - timedelta(days=_age)).strftime("%Y-%m-%d") if random.random() < 0.9 else None
		pet_data.append({
			"name": name,
			"type": type,
			"breed": breed,
			"birthday": bday
		})
	return jsonify(pet_data)

@app.route("/dev/random/receipt")
def random_receipts():
	n = int(request.args.get("n", default=100))  # number of receipts to generate
	per_hour = 4  # number of receipts per hour to simulate
	mu_price = 40.00   # mean
	sig_price = 10.00  # std. dev.
	min_price = 0.99
	tax_rate = 0.05
	discount_rate = 0.20  # 20% off
	discount_freq = 0.15  # 15% chance
	with db.engine.connect() as conn:
		cust = [c._mapping for c in conn.execute(select(customer.c.id))]
	receipt_data = []
	t = datetime.now()
	for i in range(n):
		t -= timedelta(hours=random.expovariate(per_hour))
		sub_total = round(max(min_price, random.gauss(mu_price, sig_price)), 2)
		discounts = round(sub_total * discount_rate, 2)
		tax = round((sub_total - discounts) * tax_rate, 2)
		total = round(sub_total - discounts + tax, 2)
		receipt_data.append({
			"customer_id": random.choice(cust)["id"],
			"date": t.strftime("%Y-%m-%d %H:%M:%S"),
			"sub_total": sub_total,
			"tax": tax,
			"discounts": discounts,
			"total": total
		})
	return jsonify(receipt_data)

# catch all for www/ resources
@app.route("/<path:path>")
def misc_file(path):
	return app.send_static_file(path)

@app.route("/")
def home():
	return redirect("/table/product/view")

if __name__ == "__main__":
	app.run(debug=True, port=5000)
