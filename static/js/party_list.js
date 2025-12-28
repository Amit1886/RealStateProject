// Print Party List
function printPartyList() {
    window.print();
}

// Download Table as CSV
function downloadPartyCSV() {
    let table = document.getElementById("party-table");
    let rows = table.querySelectorAll("tr");
    let csv = [];

    rows.forEach(row => {
        let cols = row.querySelectorAll("td, th");
        let rowData = [];

        cols.forEach(col => {
            rowData.push('"' + col.innerText.replace(/"/g, '""') + '"');
        });

        csv.push(rowData.join(","));
    });

    // Create CSV file
    let csvFile = new Blob([csv.join("\n")], { type: "text/csv" });
    let tempLink = document.createElement("a");
    tempLink.href = URL.createObjectURL(csvFile);
    tempLink.download = "party_list.csv";
    tempLink.click();
    tempLink.remove();
}
