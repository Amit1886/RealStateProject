$(document).ready(function () {
    $('#purchaseOrderTable').DataTable({
        pageLength: 10,
        order: [[0, 'desc']],
        responsive: true
    });
});
