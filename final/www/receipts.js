const cid = document.querySelector("#cid");
const cfnames = document.querySelector("#cfnames");
const clnames = document.querySelector("#clnames");
const cfname = document.querySelector("#cfname");
const clname = document.querySelector("#clname");

function cidUpdated() {
	for (let cnames of [cfnames, clnames]) {  // for both #cfanmes and #clnames <select>
		cnames.value = "";
		for (let option of cnames.options)
			if (option.dataset.cid === cid.value) {
				cnames.value = option.value;
				break;
			}
	}
}

function cfnamesUpdated(select) {
	let option = select.options[select.selectedIndex];
	cid.value = option.dataset.cid ?? "";
}

// cid.addEventListener("input", cidUpdated);
cid.addEventListener("change", cidUpdated);
cfnames.addEventListener("input", event => cfnamesUpdated(event.currentTarget));
cfnames.addEventListener("change", event => cfnamesUpdated(event.currentTarget));

// fill inputs onload with query string
let args = new URLSearchParams(window.location.search);
if (args.has("cid")) {
	cid.value = args.get("cid");
	cidUpdated();
}
for (let name of ["dstart", "dend"])
	document.querySelector(`input[name=${name}]`).value = args.get(name) ?? "";

// TODO: add more functionality, like disable on custom search, etc.