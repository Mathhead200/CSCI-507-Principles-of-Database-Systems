from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy import MetaData, Table, insert, select, update, delete

# Credentials for database connection including App user account
MYSQL_HOST = "localhost"
MYSQL_APP_USERNAME = "petmac_app"
MYSQL_APP_PASSWORD = 'K2EDhXXv3GfnRdkd5f7A'

# Set up Flask and SQLAlchemy
app = Flask("PetMAC Inventory Server", template_folder=".")
app.config["SQLALCHEMY_DATABASE_URI"] = f"mysql+pymysql://{MYSQL_APP_USERNAME}:{MYSQL_APP_PASSWORD}@{MYSQL_HOST}/petmac"
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# Tables in database
md = MetaData()
with app.app_context():
	product = Table("product", md, autoload_with=db.engine)
	customer = Table("customer", md, autoload_with=db.engine)
	distributor = Table("distributor", md, autoload_with=db.engine)
	receipt = Table("receipt", md, autoload_with=db.engine)
	order = Table("order", md, autoload_with=db.engine)
	receipt_line_item = Table("receipt_line_item", md, autoload_with=db.engine)
	order_line_item = Table("order_line_item", md, autoload_with=db.engine)


def render_table(table, title=None, mode = "view"):
	pk = ",".join(col.name for col in table.primary_key.columns)
	with db.engine.connect() as conn:
		selection = conn.execute(select(table))
		th = selection.keys()
		return render_template("table.j2", title=title, mode=mode, pk=pk, cols=len(th), th=th, td=selection)

# ----- Routes ----------------------------------------------------------------
@app.route("/products/view")
def view_products(title="Products"):
	return render_table(product, title=title, mode="view")

@app.route("/products/edit")
def edit_products(title="Products"):
	match request.method:
		case "GET":
			return render_table(product, title=title, mode="edit")
		case "POST":
			return "TODO: implement POST"  # TODO: stub

@app.route("/products")
@app.route("/products/")
def products():
	return redirect("/products/view")

@app.route("/customers")
def customers():
	return "TODO: /customers"  # TODO: stub

@app.route("/distributors")
def distributors():
	return "TODO: /distributors"  # TODO: stub

# inventory
@app.route("/")
def home():
	return view_products()


if __name__ == "__main__":
	app.run(debug=True, port=5000)
