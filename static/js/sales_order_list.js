$(document).ready(function () {
    $('#salesOrderTable').DataTable({
        pageLength: 10,
        order: [[0, 'desc']],
        responsive: true
    });
});
