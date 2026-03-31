/* --- SIMPLE PIN → STATE → DISTRICT DATA --- */
const pinData = {
    "110001": { state: "Delhi", district: "New Delhi" },
    "400001": { state: "Maharashtra", district: "Mumbai" },
    "560001": { state: "Karnataka", district: "Bangalore" },
    "700001": { state: "West Bengal", district: "Kolkata" }
};

/* Auto Fill State + District */
function findPin() {
    let pin = document.getElementById("pin").value;
    if (pin.length === 6 && pinData[pin]) {
        document.getElementById("state").innerHTML =
            `<option selected>${pinData[pin].state}</option>`;
        document.getElementById("district").innerHTML =
            `<option selected>${pinData[pin].district}</option>`;
    }
}

/* PRINT TABLE */
function printTable() {
    let printContent = document.getElementById("partyTable").outerHTML;
    let newWin = window.open("");
    newWin.document.write("<html><body>" + printContent + "</body></html>");
    newWin.print();
    newWin.close();
}

/* EXPORT EXCEL */
function downloadExcel() {
    let table = document.getElementById("partyTable").outerHTML;
    let data = "data:application/vnd.ms-excel," + encodeURIComponent(table);
    let a = document.createElement("a");
    a.href = data;
    a.download = "party_list.xls";
    a.click();
}

/* EXPORT PDF */
function downloadPDF() {
    alert("PDF export will require jsPDF if you want advanced layout.");
}


// Keyboard Shortcuts
document.addEventListener("keydown", function (e) {
    // CTRL + S => Save
    if (e.ctrlKey && e.key === "s") {
        e.preventDefault();
        document.querySelector("form").submit();
    }

    // ALT + N => New Party
    if (e.altKey && e.key === "n") {
        window.location.href = "/khataapp/add-party/";
    }

    // ALT + L => Party List
    if (e.altKey && e.key === "l") {
        window.location.href = "/khataapp/party-list/";
    }
});
