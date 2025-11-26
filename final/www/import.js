let form = document.forms.import;
let textarea = form.elements.json;

document.querySelector("#random").addEventListener("click", () => {
	let n = document.querySelector("#n").value;
	if (n)  n = "n=" + n;
	fetch(`/dev/random/${window.TABLE}?${n}`, {
		method: "GET"
	}).then(async response => {
		if (!response.ok)  throw new Error(await response.text());
		return response.json();  // try to parse HTTP response as JSON

	}).then(data => {
		textarea.value = JSON.stringify(data, null, 4);

	}).catch(error => {
		console.error("Response (error):", error);
		page = window.open("", "_blank");
		page.document.write(error.message);
		page.document.close();  // render
	});
});

form.addEventListener("submit", event =>{
	event.preventDefault();
	fetch(form.action, {
		method: form.method,
		headers: { "Content-Type": "application/json" },
		body: textarea.value  // IMPORTANT: No stringify or Flask will see it as 'str' instead of 'list'
	}).then(async response => {
		if (!response.ok)  throw new Error(await response.text());
		return response.json();  // try to parse HTTP response as JSON

	}).then(data => {
		console.log("Response (data):", data);
		if (confirm(`Import successful! ${data.rowcount} rows updated. View?`))
			location.href = `/table/${window.TABLE}/view`;  // refreash

	}).catch(error => {
		console.error("Response (error):", error);
		page = window.open("", "_blank");
		page.document.write(error.message);
		page.document.close();  // render
	});
});