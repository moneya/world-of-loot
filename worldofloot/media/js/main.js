function AddItemModal() {
  this.Init = function() {
    var me = this;

    // Autocomplete
    $("#add-item-id").autocomplete({
      minLength: 2,
      source: function(request, response) {
        $.getJSON('/autocomplete/' + request.term, function(data) {
          var arr = [];
          for (var i=0; i < data.length; i++) {
            arr.push({data: data[i],
              label: data[i].name, value: data[i].name});
          }
          response(arr);
        });
      },
      select: function(event, ui) {
        if (ui.item) {
          me.LoadImage(ui.item.data.id, ui.item.data.type);
        }
      }
    // TODO format to use data[i].name
    });

    $('#add-item-id').on('keydown', function(e) {
      var $submit = $('#add-item button.btn-add-item');
      if (e.keyCode == 13 && !$submit.hasClass('disabled')) {
        $submit.click();
      }
    });


    // Submit button
    $('#add-item button.btn-add-item').on('click', function() {
      // TODO some sort of loader
      $.get('/add/' + me.id, function(data) {

        $('#add-item').modal('hide');
        window.location.reload();
      }, 'json');
    });

    // Show modal dialog
    $('a.js-add-pin').on('click', function() {
      $('#add-item-image-container').empty();
      $('#add-item').modal();
      $('#add-item-id').val('').focus()
    });

    // Pin deletion
    $('.delete-pin').on('click', function() {
      var type = $(this).data('item-type');
      var id = $(this).data('item-id');
      $.getJSON('/remove/' + type + '/' + id, function(data) {
        window.location.reload();
      });
    });
  }

  this.LoadImage = function(id, type) {
    // Loads image after user selection
    var me = this;
    me.loaded_image = false;
    $('#add-item-loader').show();
    $.getJSON('/info/' + type + '/' + id, function(data) {
      $('#add-item-loader').hide();
      if (!data || !data.images) {
        alert("Sorry, I couldn't find this item.  Please try something different.");
        return;
      }

      $('#add-item-image-container').html('<a href="#" rel="'
        + type + '=' + id + '"><h3>' + data.name
        + '</h3><img src="' + data.images[0] + '"/></a>');

      $('#add-item button').removeClass('disabled');
      me.id = id;
      me.loaded_image = true;
    });
  }
}

$(function() {
  var $handler = $('#pins .pin');
  $handler.imagesLoaded(function() {
    $handler.wookmark({
      offset: 10,
      itemWidth: 260,
      autoResize: true,
    });
    /*
    $handler.masonry({
      itemSelector: '.pin',
      columnWidth: 300,
    });
    */
  });

  var add_modal = new AddItemModal();
  add_modal.Init();
});
