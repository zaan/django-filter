
function get_form_prefix(field_name) {
	try {
		return field_name.match(/^[a-z0-9]+\-/)[0];
	}
	catch(e) {
		return '';
	}
}

function add_fieldset_callback() {
	add_fieldset($(this).parent());
	$(this).addClass('disabled');
}

function get_option(key, prefix) {
	var field = options[key];
	var widget_obj = $(field['widget']);
	var label_obj = $(field['label_tag']);
	if( widget_obj.length > 1 ) {
		widget_obj.each(function() {
			$(this).attr('name', $(this).attr('name').replace(/[a-z0-9]+\-/, prefix));
			$(this).attr('id', $(this).attr('id').replace(/[a-z0-9]+\-/, prefix));
		});
	}
	else {
		widget_obj.attr('name', widget_obj.attr('name').replace(/[a-z0-9]+\-/, prefix));
		widget_obj.attr('id', widget_obj.attr('id').replace(/[a-z0-9]+\-/, prefix));
	}
	label_obj.attr('for', label_obj.attr('for').replace(/[a-z0-9]+\-/, prefix));
	field['widget'] = $('<div>').append(widget_obj).html();
	field['label_tag'] = $('<div>').append(label_obj).html();
	return field;
}

function add_fieldset(el) {
	var group_total_forms = $('#id_group-total-forms').val();
	group_total_forms++;
	var select_field = $('#filters fieldset:first select[name$=select_field]').parents('.form-row').clone();
	
	select_field.find('select').attr('name', group_total_forms+'-select_field');
	select_field.find('select').attr('id', 'id_'+group_total_forms+'-select_field');
	select_field.find('label').attr('for', group_total_forms+'-select_field');
	$(el).after('<fieldset id="'+group_total_forms+'-fieldset" />');
	$(el).next().append('<a class="close">×</a>');
	$(el).next().append(select_field);
	$(el).next().after($(el).clone());
	$('#filters .or .btn:last').one('click', add_fieldset_callback);
	inc_total_forms();
}

function inc_total_forms() {
	var group_total_forms = $('#id_group-total-forms').val();
	group_total_forms++;
	$('#id_group-total-forms').val(group_total_forms);
}

function dec_total_forms() {
	var group_total_forms = $('#id_group-total-forms').val();
	group_total_forms--;
	$('#id_group-total-forms').val(group_total_forms);
}

function rebuild_form_indexes()
{
	$('#filter-form fieldset').each(function(index) {
		var i = index+1;
		$(this).attr('id', i+'-fieldset');
		$(this).find('label').each(function() {
			new_attr_val = $(this).attr('for').replace(/[0-9]+\-/, i+'-');
			$(this).attr('for', new_attr_val);
		});
		
		$(this).find('select, input, textarea').each(function() {
			new_attr_val = $(this).attr('id').replace(/[0-9]+\-/, i+'-');
			$(this).attr('id', new_attr_val);
			new_attr_val = $(this).attr('name').replace(/[0-9]+\-/, i+'-');
			$(this).attr('name', new_attr_val);
		});
	});
}



$(function () {
	
	$('#filters fieldset .form-row').each(function(index) {
		if( !$(this).find('select').is('[name$=select_field]') )
			$(this).find('.controls').append('&nbsp;<span class="well rm_field"><i class="icon-minus-sign icon-white"></i></span></p>');
	});
	
	$('select[name$=select_field]').live('change', function() {
		var prefix = get_form_prefix($(this).attr('name'));
		var fieldset = $('#'+prefix+'fieldset');
		var field = get_option($(this).val(), prefix);
		var row = '<div class="control-group form-row">\
				   <label class="control-label" for="'+$(this).val()+'">'+field['label']+'</label>\
				   <div class="controls">'+ field['widget']+'&nbsp;<span class="well rm_field"><i class="icon-minus-sign icon-white"></i></span></div></div>';
		fieldset.append(row);
		$(this).val('');
	});
	
	$('.rm_field').live('click', function() {
		$(this).parents('.form-row').remove();
	});
	
	$('#filters .or .btn:last').one('click', add_fieldset_callback);
	
	$('#filters .close').live('click', function() {
		$(this).parent().next().remove();
		$(this).parent().remove();
		if( $('#filters fieldset').length < 2 ) {
			$('#filters fieldset .close').remove();
		}
		dec_total_forms();
		rebuild_form_indexes();
		$('#filters .or .btn:last').removeClass('disabled').unbind('click').one('click', add_fieldset_callback);
	});
});
