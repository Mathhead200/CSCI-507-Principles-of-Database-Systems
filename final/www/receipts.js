const cid = document.querySelector("#cid");
const cfnames = document.querySelector("#cfnames");
const clnames = document.querySelector("#clnames");
const cfname = document.querySelector("#cfname");
const clname = document.querySelector("#clname");
function cfnamesUpdated(event) {
	let select = event.currentTarget;
	let option = select.options[select.selectedIndex];
	cid.value = option.dataset.cid;
	console.log(select, option, cid.value);
}
cfnames.addEventListener("input", cfnamesUpdated);
cfnames.addEventListener("change", cfnamesUpdated);

// TODO: add more functionality, like disable on custom search, etc.