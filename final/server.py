from flask import Flask, request, render_template, render_template_string, jsonify, abort, redirect
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData, Table, insert, select, update, delete, and_
from sqlalchemy.orm import Session
from werkzeug.exceptions import HTTPException

# Credentials for database connection including App user account
MYSQL_HOST = "localhost"
MYSQL_APP_USERNAME = "petmac_app"
MYSQL_APP_PASSWORD = 'K2EDhXXv3GfnRdkd5f7A'

# Set up Flask and SQLAlchemy
app = Flask("PetMAC Inventory Server", template_folder=".", static_folder=".")
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

	accessible_tables = [product, customer, distributor, pet]
	accessible_tables = { table.name : table for table in accessible_tables }

# ----- Routes ----------------------------------------------------------------
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
		statements.append( update(table).values(**normalize_for_sql(obj["values"])).where(predicate))
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
	return jsonify(success=True, rowcount=rowcount, log=log)  # in case a payload is expected

@app.route("/<path:path>")
def misc_file(path):
	return app.send_static_file(path)

@app.route("/")
def home():
	return redirect("/table/product/view")

if __name__ == "__main__":
	app.run(debug=True, port=5000)
