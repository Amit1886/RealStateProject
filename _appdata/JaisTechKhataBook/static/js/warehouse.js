$(document).ready(function () {

    $('#warehouseTable').DataTable({
        pageLength: 5,
        lengthMenu: [5, 10, 25, 50],
        ordering: true,
        searching: true,
        info: true,
        responsive: true,
        language: {
            search: "Search:",
            lengthMenu: "Show _MENU_ entries",
            info: "Showing _START_ to _END_ of _TOTAL_ records",
            paginate: {
                previous: "‹",
                next: "›"
            }
        },
        columnDefs: [
            { targets: -1, orderable: false }
        ]
    });

});
