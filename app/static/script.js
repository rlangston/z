// Note: have to use classes for some things as id is used for the item number

$(document).ready(function() {

    // Function to apply click handlers to list items
    function applyHandlers(item) {
        // jQuery click event handler for list items
        $(item).on('click', function() {
            end_editing(); // ensure that not in edit mode
            const id = $(this).attr('id');
            update_text(id);
            update_buttons(id);
        });
    }

    // let draggedItem = null;

    // apply handlers to each existing item
    $('.item').each(function(index) {
        applyHandlers(this);
    });

    // if the hidden id variable is not 0 then update text and buttons
    id = $('#selectedid').val();
    if (id != "0") {
        update_text(id);
        update_buttons(id);
    }

    // Search box handle ENTER
    $('#search').keypress(function(event){
        // Check if the Enter key is pressed (key code 13)
        if (event.which == 13) {
            reload_page();
        }
    });

    // Tag box handle ENTER
    $('#tags').keypress(function(event){
        // Check if the Enter key is pressed (key code 13)
        if (event.which == 13) {
            reload_page();
        }
    });

    $('#browse-btn').on('click', function() {
        $('#modal').show();
        // Send an AJAX request to fetch data based on the item id
        $.ajax({
            url: '/tags',
            method: 'POST',
            dataType: 'text', // Expect a json response
            success: function(response) {
                const text = response;
                // Update the modal's html with the response text
                $("#modal-text").html(text);

                // Get the values from the input box, split by spaces, and store in an array
                var tagValues = $('#tags').val().split(' ');

                // Uncheck all checkboxes first to reset
                $('input[name="selectedtags"]').prop('checked', false);

                // Loop through each checkbox and check if its value is in the tagValues array
                $('input[name="selectedtags"]').each(function() {
                    if (tagValues.includes($(this).val())) {
                        $(this).prop('checked', true);
                    }
                });

            },
            error: function(xhr, status, error) {
                console.log('Error:', error);
                // Optionally, handle the error by showing a message
                $('#modal-text').html('Failed to load tags data');
            }
        });

    });

    $('#clear-search-btn').click(function() {
        $('#tags').val('')
        $('#search').val(''); // Clear the inputs
        reload_page();
    });

    $('#clear-btn').click(function() {
        $('input[name="selectedtags"]').prop('checked', false);
    });

    $('#ok-btn').on('click', function() {
        close_modal();
    });

    $('#cancel-btn').on('click', function() {
        close_modal_cancel();
    });

    // If click outside the modal then cancel
    $(window).on('click', function(event) {
        if ($(event.target).is('#modal')) {
            close_modal_cancel();
        }
    });

    // jQuery click event handler for discard button - need to use class as id used for item number
    $('.discard-btn').on('click', function() {
        const itemId = $(this).attr('id');

        // Send an AJAX request to fetch data based on the item id
        $.ajax({
            url: '/zettel',
            method: 'POST',
            contentType: 'application/json', // Specify that you're sending JSON
            dataType: 'json', // Expect a JSON response
            data: JSON.stringify({
                id: itemId
            }),
            success: function(response) {
                const {text, markdown} = response;
                // Update the right pane's text area with the response text
                $('#text-area').val(text);
                $('#viewtext').html(markdown);
                end_editing();
            },
            error: function(xhr, status, error) {
                console.log('Error:', error);
                // Optionally, handle the error by showing a message
                $('#viewtext').html("Failed to load data for item: " + itemId);
            }
        });
    });

    // jQuery click event handler for save button - need to use class as id used for item number
    $('.save-btn').on('click', function() {
        const itemId = $(this).attr('id');
        const buttonText = $(this).text(); // current button text
        if (itemId == "0") { // No item selected
            return;
        }

        if (buttonText == "Edit") { // go into edit mode
            start_editing();
        } else { // save and go back to view mode
            // Send an AJAX request to fetch data based on the item id
            $.ajax({
                url: '/savezettel',
                method: 'POST',
                contentType: 'application/json', // Specify that we are sending JSON
                dataType: 'json', // Expect a JSON response
                data: JSON.stringify({
                    id: itemId,
                    body: $('#text-area').val()
                }),
                success: function(response) {
                    const {title, date, tags, text, markdown} = response;
                    const item = $('li[id="' + itemId + '"]');
                    item.find('.item-title').text(title + " (#" + itemId + ")");
                    item.find('.date').text(date);
                    item.find('.description').text(tags);
                    // Update the right pane's text area with the response text
                    $("#viewtext").html(markdown);
                    $('#text-area').val(text);

                },
                error: function(xhr, status, error) {
                    console.log('Error:', error);
                    // Optionally, handle the error by showing a message
                    $('#text-area').val('Failed to load data for item: ' + itemId);
                }
            });

            end_editing();
        }
    });

    // jQuery click event handler for delete button - need to use class as id used for item number
    $('.delete-btn').on('click', function() {
        const itemId = $(this).attr('id');
        if (itemId == "0") { // No item selected
            return;
        }

        // Send an AJAX request to fetch data based on the item id
        $.ajax({
            url: '/deletezettel',
            method: 'POST',
            contentType: 'application/json', // Specify that you're sending JSON
            dataType: 'json', // Expect a JSON response
            data: JSON.stringify({
                id: itemId
            }),
            success: function(response) {
                $('.item#' + itemId).remove()
                $('#text-area').val("");
                $('#viewtext').html("");
                // Set the id of the buttons to 0
                $('.save-btn').attr('id', '0');
                $('.discard-btn').attr('id', '0');
                $('.delete-btn').attr('id', '0');
                end_editing();
            },
            error: function(xhr, status, error) {
                console.log('Error:', error);
                $('#viewtext').html('Failed to load data for item: ' + itemId);
                end_editing();
            }
        });
    });

    // jQuery click event handler for new button - need to use class as id used for item number
    $('.new-btn').on('click', function() {
        // Send an AJAX request to fetch data based on the item id
        $.ajax({
            url: '/newzettel',
            method: 'POST',
            dataType: 'json', // Expect a JSON response
            success: function(response) {
                const { id, title, date, tags, text, markdown } = response;

                const newItem = $('<li class="item" id="' + id + '">' +
                                    '<div class="item-title">' + title + ' (#' + id + ')</div>' +
                                    '<div class="item-details">' +
                                        '<span class="date">' + date + '</span>' +
                                        '<span class="description">' + tags + '</span>' +
                                    '</div>' +
                                  '</li>');

                // Append the new item to the list and apply handlers
                $('#item-list').append(newItem);
                applyHandlers(newItem[0]);

                // Update the text and the markdown
                $("#viewtext").html(markdown);
                $('#text-area').val(text);

                // Set the id of the buttons to the new item's id
                update_buttons(id);

                start_editing();
            },
            error: function(xhr, status, error) {
                console.log('Error:', error);
                // Optionally, handle the error by showing a message
                $('#text-area').val('Failed to create data ');
            }
        });
    });
});

function start_editing() {
    $("#viewtext").hide();
    $("#edittext").show();
    $(".discard-btn").show();
    // $(".delete-btn").show();
    $('.save-btn').text("Save");
}

function end_editing() {
    $("#edittext").hide();
    $("#viewtext").show();
    $(".discard-btn").hide();
    // $(".delete-btn").hide();
    $(".save-btn").text("Edit")
}

function reload_page() {
    const tags = $('#tags').val()
    const query = $('#search').val(); // Get the value from the input
    const url = "/index?q=" + query + "&tags=" + tags; // Construct the URL

    // Redirect to the new page
    window.location.href = url;
}

function close_modal() {
    let selectedTags = $('input[name="selectedtags"]:checked').map(function() {
        return this.value;
    }).get().join(' ');
    $('#tags').val(selectedTags);
    $('#modal').hide();
    reload_page();
}

function close_modal_cancel() {
    $('#modal').hide();
}

function update_text(itemId) {
    $.ajax({
        url: '/zettel',
        method: 'POST',
        contentType: 'application/json', // Specify that you're sending JSON
        dataType: 'json', // Expect a JSON response
        data: JSON.stringify({
            id: itemId
        }),
        success: function(response) {
            const {text, markdown} = response;
            // Update the right pane's text area with the response text
            $("#viewtext").html(markdown);
            $('#text-area').val(text);
        },
        error: function(xhr, status, error) {
            console.log('Error:', error);
            // Optionally, handle the error by showing a message
            $('#viewtext').html('Failed to load data for item: ' + itemId);
            $('#text-area').val('Failed to load data for item: ' + itemId);
        }
    });
}

function update_buttons(itemId) {
    // Set the id of the buttons to the itemId
    $('.save-btn').attr('id', itemId);
    $('.discard-btn').attr('id', itemId);
    $('.delete-btn').attr('id', itemId);
}
