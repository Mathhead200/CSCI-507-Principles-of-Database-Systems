
const PK = document.forms.vars.pk.value.split(",");   // primary keys
const TABLE = document.forms.vars.table.value;        // name of table
const MODE = document.forms.vars.mode.value;          // "view" or "edit"
const COLS = Number(document.forms.vars.cols.value);  // number of columns in table

const table = document.querySelector("#edit-table");  // actaully a <form> container

// filters
const FILTER_STORE = TABLE + ".hidden";  // name for filter storage
let hidden = new Set(localStorage.getItem(FILTER_STORE)?.split(","));  // hidden cols stored as comma seperated string; e.g. "A,B,C"
let checkboxes = document.forms.filters.querySelectorAll(".show-filter input");
function updateCol(col, show) {
	// show or hide (!show) column with given name
	for (let tx of table.querySelectorAll(`tr > *[data-col='${col}']`))
		if (show)  tx.classList.remove("hide");
		else       tx.classList.add("hide");
}
for (let checkbox of checkboxes) {
	let {col} = checkbox.dataset;
	updateCol(col, checkbox.checked = !hidden.has(col));
	checkbox.addEventListener("input", () => {
		updateCol(col, checkbox.checked);
		if (checkbox.checked)  hidden.delete(col);
		else                   hidden.add(col);
		localStorage.setItem(FILTER_STORE, [...hidden].join(","));
	});
}

// finish initializing table
if (MODE == "edit") {
	let modifiedEleCount = 0;  // track if any elements are currently modified
	let submitBtn = table.querySelector("input[type='submit']");

	// How many times each pk value appears in the table
	let pk_tally = Object.fromEntries(PK.map(pk => [pk, new Map()]));  // { pk[0]: {val_i: count_i, ...}, pk[1]: {val_j, count_j}, ... }
	let pks_unique = true;

	function validRow(tr) {
		return true;  // TODO: (remove/redesign) some tables can have null PKs becasue of AUTO INCREMENT
		/*
		// either no null PKs, or everything is empty
		return tr.querySelectorAll("input.pk-null").length == 0 ||
			[...tr.querySelectorAll("input")].every(input => !input.value);
		*/
	}

	function syncSubmitBtn(input) {
		submitBtn.disabled = modifiedEleCount == 0 || !pks_unique || !validRow(input.closest("tr"));
	}

	function addModified(ele) {
		if (!ele.classList.contains("modified")) {
			ele.classList.add("modified");
			modifiedEleCount++;
			syncSubmitBtn(ele);
		}
	}

	function removeModified(ele) {
		if (ele.classList.contains("modified")) {
			ele.classList.remove("modified");
			modifiedEleCount--;
			syncSubmitBtn(ele);
		}
	};

	function addInputListeners(input) {
		function onInput(input) {
			// check if modified
			if (input.value != (input.dataset.initValue ?? ""))
				addModified(input);
			else
				removeModified(input);
			
			// ensure pk non-null
			if (PK.includes(input.dataset.col)) {
				if (!input.value)
					input.classList.add("pk-null");
				else
					input.classList.remove("pk-null");
			}
		}

		// revert to default value
		input.addEventListener("keydown", event => {
			if (event.key !== "Escape")  return;
			let ele = event.currentTarget;
			ele.value = ele.dataset.initValue ?? "";
			removeModified(ele);
			event.preventDefault();
			onInput(input);
		});

		// auto-fill input with placeholder value
		input.addEventListener("keydown", event => {
			if (event.key !== " ")  return;
			let ele = event.currentTarget;
			if (ele.value.trim().length > 0)  return;
			ele.value = ele.placeholder;
			event.preventDefault();
			onInput(input);
		});

		// up/down table navigation
		input.addEventListener("keydown", event => {
			let UP = event.key === "ArrowUp";
			if (!(UP || event.key === "ArrowDown"))  return;
			let input = event.currentTarget;
			let {col} = input.dataset;
			let tr = input.closest("tr");
			let dest;
			if (UP) {
				dest = tr.previousElementSibling ?? tr.parentElement.lastElementChild.previousElementSibling;
			} else {
				dest = tr.nextElementSibling;
				if (dest == tr.parentElement.lastElementChild)
					dest = tr.parentElement.firstElementChild;
			}
			dest.querySelector(col ? `input[data-col=${col}]` : "td:last-child input").focus();
			event.preventDefault();
		});

		// track which fields are modified from their original values
		input.addEventListener("input", event => {
			onInput(event.currentTarget);
		});
		input.addEventListener("change", event => {
			let input = event.currentTarget;
			input.value = input.value.trim();
			onInput(input);
		});

		// keep pk_tally up to date
		let focusedPK = null;
		input.addEventListener("focus", event => {
			let input = event.currentTarget;
			let {col} = input.dataset;
			if (!PK.includes(col))  return;  // not a primary key field
			let {value} = input;
			let count = pk_tally[col].get(value) - 1;
			if (count > 0)
				pk_tally[col].set(value, count);
			else
				pk_tally[col].delete(value);
			focusedPK = value; // track for potential error clearing on blur
		});
		input.addEventListener("blur", event => {
			let input = event.currentTarget;
			let {col} = input.dataset;
			if (!PK.includes(col))  return;  // not a primary key field
			pks_unique = true;
			
			// check old value too
			let count = pk_tally[col].get(focusedPK);  // may be undefined
			if (count === 1) {
				// we have resolved a previous error; clear conflicts
				for (let match of table.querySelectorAll(`input[data-col=${col}]`))
					if (match.value === focusedPK)
						match.classList.remove("pk-dup")
			} else if (count > 1) {
				pks_unique = false;  // didn't resolve that previous error
			}
			focusedPK = null;  // to be safe

			// is current value in conflict?
			let {value} = input;
			if (pk_tally[col].has(value)) {
				// duplicate pk
				pk_tally[col].set(value, pk_tally[col].get(value) + 1);
				for (let match of table.querySelectorAll(`input[data-col=${col}]`))
					if (match.value === value)
						match.classList.add("pk-dup")
				pks_unique = false;
			} else {
				// unique pk
				pk_tally[col].set(value, 1);
				input.classList.remove("pk-dup");
			}
			syncSubmitBtn(input);
		});
	}

	function pk(input) {
		let ret;
		if (ret = PK.includes(input.dataset.col))
			input.classList.add("pk");
		return ret;
	}

	// Activate input all input fields in table
	let ths = table.querySelectorAll("thead tr:first-of-type th:not(:empty)");
	console.assert(ths.length == COLS, { COLS, ths });  // DEBUG

	let rows = table.querySelectorAll("tbody tr");
	const ROWS = rows.length - 1;
	const ADD_BTN = rows[ROWS];  // on last row

	for (let th of ths)
		if (PK.includes(th.innerText.trim()))
			th.classList.add(".pk");

	for (let i = 0; i < ROWS; i++)
		for (let input of rows[i].querySelectorAll("input")) {
			input.placeholder = input.dataset.initValue;
			if (pk(input))
				pk_tally[input.dataset.col].set(input.value, 1);  // initialize pk_tally
			addInputListeners(input);
		}

	// Activate + button at bottom of table
	function addRecord() {
		let tr = document.createElement("tr");
		tr.classList.add("insert");
		for (let i = 0; i < COLS; i++)
			tr.append(document.createElement("td"));
		let temp_td = document.createElement("td");
		temp_td.innerHTML = "<label>*New*</label>";
		tr.append(temp_td);
		
		// copy values from bottom row as placeholder examples, or just column names if no example rows exist
		let placeholders = (
			ROWS > 0
			? [...rows[ROWS - 1].querySelectorAll("input")].map(input => input.value)
			: [...ths].map(th => th.innerText)
		);

		for (let [i, td] of tr.querySelectorAll("td").entries()) {
			let input = document.createElement("input");
			let col = ths[i]?.innerText.trim();
			if (!col)  continue;  // skip this td
			td.dataset.col = col;
			if (hidden.has(col))  td.classList.add("hide");
			input.type = "text";
			input.name = `petmac-${TABLE}-${col}`;
			input.dataset.col = col;
			input.placeholder = placeholders[i];
			if (pk(input))  input.classList.add("pk-null");
			addInputListeners(input);
			td.append(input);
		}

		table.querySelector("tbody").insertBefore(tr, ADD_BTN);
	}
	table.querySelector("#add-record").addEventListener("click", addRecord);
	document.addEventListener("keydown", event => {
		if (!(event.key === "Enter" && event.shiftKey))  return;
		event.preventDefault();
		addRecord();
	});

	// Activate delete buttons
	for (let btn of table.querySelectorAll(".delete"))
		btn.addEventListener("input", () => {
			let tr = btn.closest("tr");
			if (btn.checked)  tr.classList.add("delete");
			else              tr.classList.remove("delete");
			
			for (let input of tr.querySelectorAll("input[name]"))
				input.disabled = btn.checked;
		});

	// handle form submition
	submitBtn.form.addEventListener("submit", event => {
		event.preventDefault();

		let deletes = [];  // records to be deleted (pk only)
		let inserts = [];  // new records (values only)
		let updates = [];  // record updates and modifications (old pk along with new values)

		let rows = [...table.querySelectorAll("tbody tr")];  // shadow rows variable to now be all rows including newly added rows
		let len = rows.length - 1;  // ignore the + button row
		for (let i = 0; i < len; i++) {
			let tr = rows[i];
			
			let pk = {};  // initial value for the primary key
			for (let input of tr.querySelectorAll(".pk"))
				pk[input.dataset.col] = input.dataset.initValue;  // init pk value in case it is changing (i.e. UPDATE)
			
			let values = {};  // get the modified values
			for (let input of tr.querySelectorAll(".modified"))
				values[input.dataset.col] = input.value.trim();  // populate SQL values with  .modified fields

			if (tr.classList.contains("delete"))       // first check if this record is pending deletion
				deletes.push({pk});
			else if (tr.classList.contains("insert"))  // next, is this a new record?
				inserts.push({values});
			else if (Object.keys(values).length > 0)   // has anything beenn modified on this row?
				updates.push({pk, values});
			// else, skip row
		}

		// send update, insert, and delete requests to server via POST
		request = { deletes, inserts, updates };
		console.log("Request:", request);  // DEBUG: stub
		fetch(table.action, {
			method: table.method,
			headers: { "Content-Type": "application/json" },
			body: JSON.stringify(request)  // do I need to stringify here?

		}).then(async response => {
			if (!response.ok)  throw new Error(await response.text());
			return response.json();  // try to parse HTTP response as JSON

		}).then(data => {
			console.log("Response (data):", data);
			if (confirm(`Update successful! ${data.rowcount} rows updated. Refresh?`))
				location.reload();  // refreash

		}).catch(error => {
			console.error("Response (error):", error);
			page = window.open("", "_blank");
			page.document.write(error.message);
			page.document.close();  // render
		});
	});
}
