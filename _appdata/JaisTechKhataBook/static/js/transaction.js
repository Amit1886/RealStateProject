$(document).ready(function () {

    let table = $('#transactionTable').DataTable({
        pageLength: 10,
        ordering: true,
        responsive: true,
        dom: 'Bfrtip',
        buttons: [
            { extend: 'print', title: 'Transaction List' },
            { extend: 'excelHtml5', title: 'Transaction List' },
            { extend: 'pdfHtml5', title: 'Transaction List' }
        ],
        columnDefs: [
            { targets: -1, orderable: false }
        ]
    });

    // Custom filters
    $('#partyFilter').on('keyup', function () {
        table.column(0).search(this.value).draw();
    });

    $('#typeFilter').on('change', function () {
        table.column(1).search(this.value).draw();
    });

    // Buttons trigger
    $('#btnPrint').click(() => table.button('.buttons-print').trigger());
    $('#btnExcel').click(() => table.button('.buttons-excel').trigger());
    $('#btnPdf').click(() => table.button('.buttons-pdf').trigger());

});
