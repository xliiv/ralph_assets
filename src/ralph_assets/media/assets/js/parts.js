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
			this.id_regex = new RegExp('(' + this.prefix + '-\\d+)');

			var self = this;
			if(this.observe_last) {
				$('input', self.formset_selector)
					.bind('keydown', function(event){
						var val = $(this).val();
						if(val !== '') {
							$(this).closest(self.row_element).removeClass('empty');
						}
						if(event.keyCode === 13) {
							event.preventDefault();
							if(val !== '') {
								self.fetch_info($(this).parent());
								var $row = $(self.row_element + '.empty', self.formset_selector);
								if ($row.length === 0){
									$row = self.add_row();
								}
								$('input:first', $row).focus();
								self.fetch_info($('td:first', $row), 'Fill field.');
							}
						}
					});
			}
		}

		Formset.prototype.get_last_row = function() {
			return $(this.row_element + ':last', this.formset_selector);
		};

		Formset.prototype.update_row = function(element, idx) {
			var replacement = this.prefix + '-' + idx;
			var attrs = ['for', 'id', 'name'];
			var self = this;
			$.each(attrs, function(index, value){
				var e = $('[' + value +']', element);
				if (e.length) {
					$(e).attr(value, $(e).attr(value).replace(self.id_regex, replacement));
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
			$(row).addClass('empty');
			return $(row);
		};

		Formset.prototype.fetch_info = function(element, text) {
			var url = $(element).data('url') || false;
			var target = $(element).data('target') || false;
			if (!url && !target) {
				return false;
			}
			var $target = $(element).siblings('.' + target);
			var result = text || false;
			var self = this;
			if (!result) {
				var $input = $('input', element);
				var attr = $input.attr('name').replace(this.id_regex, '').slice(1);
				var data = {};
				data[attr] = $input.val();
				$.ajax({
					method: 'GET',
					url: url,
					data: data
				})
				.done(function(data) {
					$(target).closest(self.row_element).addClass('success');
					$target.html(data);
				})
				.fail(function(jqXHR) {
					switch (jqXHR.status) {
						case 400:
							$target.html('zle dane');
							break;
						case 404:
							$target.html('taki part nie istnieje');
							break;
					}
				});
			}
			$target.html(result);

		};
		return Formset;

	})();
	new Formset($('.add-formset'), 'add', 'tr', true);
	new Formset($('.delete-formset'), 'delete', 'tr', true);
});
