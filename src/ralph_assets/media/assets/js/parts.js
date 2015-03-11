$(document).ready(function () {
	'use strict';
	var Formset;

	Formset = (function() {
		// works only with fields wrapped by other element
		function Formset(formset_selector, prefix, row_element, observe_last) {
			this.formset_selector = formset_selector;
			this.prefix = prefix;
			this.total_forms = $('#id_' + this.prefix + '-TOTAL_FORMS', formset_selector);
			this.initial_forms = $('#id_' + this.prefix + '-INITIAL_FORMS', formset_selector);
			this.max_num_forms = $('#id_' + this.prefix + '-MAX_NUM_FORMS', formset_selector);
			this.row_element = row_element || 'div';
			this.observe_last = observe_last || false;

			var self = this;
			if(this.observe_last) {
				$('input', self.formset_selector).bind('keydown', function(event){
					if(event.keyCode === 13) {
						self.fetch_info($(this).parent());
						event.preventDefault();
						var new_row = self.add_row();
						$('input:first', new_row).focus();
					}
				});
			}
		}

		Formset.prototype.get_last_row = function() {
			return $(this.row_element + ':last', this.formset_selector);
		};

		Formset.prototype.update_row = function(element, idx) {
			var id_regex = new RegExp('(' + this.prefix + '-\\d+)');
			var replacement = this.prefix + '-' + idx;
			var attrs = ['for', 'id', 'name'];
			$.each(attrs, function(index, value){
				var e = $('[' + value +']', element);
				if (e.length) {
					$(e).attr(value, $(e).attr(value).replace(id_regex, replacement));
				}
			});
		};

		Formset.prototype.add_row = function() {
			var form_count = parseInt(this.total_forms.val());
			var row = $(this.row_element + ':first', this.formset_selector).clone(true).get(0);
			$(row).insertAfter(this.get_last_row());
			this.total_forms.val(form_count + 1);
			this.update_row(row, form_count);
			$('input', row).val('');
			return $(row);
		};

		Formset.prototype.fetch_info = function(element) {
			var url = $(element).data('url') || false;
			var target = $(element).data('target') || false;
			if (!url && !target) {
				return false;
			}
			$target = $(element).siblings('.' + target);

		};
		return Formset;

	})();
	new Formset($('.add-formset'), 'add', 'tr', true);
	new Formset($('.delete-formset'), 'delete', 'tr', true);
});
