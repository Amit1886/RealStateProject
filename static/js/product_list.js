$(document).ready(function () {

    // ✅ INIT DATATABLE
    let table = $('#productTable').DataTable({
        pageLength: 10,
        lengthMenu: [10, 25, 50, 100],
        ordering: true,
        responsive: true,
        processing: true,
        dom: 'Bfrtip',

        buttons: [
            {
                extend: 'excelHtml5',
                title: 'Products'
            },
            {
                extend: 'pdfHtml5',
                title: 'Products'
            },
            {
                extend: 'print',
                title: 'Products'
            }
        ]
    });

    // ✅ MULTI FILTER (PARTY LIST STYLE)
    function applyFilters() {
        table
            .column(1).search($('#filterCategory').val()) // Category
            .column(2).search($('#filterName').val())     // Product Name
            .column(5).search($('#filterSKU').val())      // SKU
            .column(8).search($('#filterGST').val())      // GST
            .draw();
    }

    // 🔍 INPUT EVENTS
    $('#filterCategory, #filterName, #filterSKU, #filterGST')
        .on('keyup change', function () {
            applyFilters();
        });

    // ♻️ RESET
    $('#resetFilters').on('click', function () {
        $('.filter-card input').val('');
        table.search('').columns().search('').draw();
    });

});
