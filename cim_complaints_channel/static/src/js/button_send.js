odoo.define('cim_complaints_channel.animation', function (require) {
    'use strict';

    var ajax = require('web.ajax');
    var snippet_animation = require('web_editor.snippets.animation');

    snippet_animation.registry.form_builder_send.include({
        /**
         * @override
         */
        send: function(e) {
            e.preventDefault();  // Prevent the default submit behavior
            this.$target.find('.o_website_form_send').off().addClass('disabled');  // Prevent users from crazy clicking

            var self = this;

            self.$target.find('#o_website_form_result').empty();
            if (!self.check_error_fields([])) {
                self.update_status('invalid');
                return false;
            }

            // Prepare form inputs
            this.form_fields = this.$target.serializeArray();
            _.each(this.$target.find('input[type=file]'), function(input) {
                $.each($(input).prop('files'), function(index, file) {
                    // Index field name as ajax won't accept arrays of files
                    // when aggregating multiple files into a single field value
                    self.form_fields.push({
                        name: input.name + '[' + index + ']',
                        value: file
                    });
                });
            });

            // Serialize form inputs into a single object
            // Aggregate multiple values into arrays
            var form_values = {};
            _.each(this.form_fields, function(input) {
                if (input.name in form_values) {
                    // If a value already exists for this field,
                    // we are facing a x2many field, so we store
                    // the values in an array.
                    if (Array.isArray(form_values[input.name])) {
                        form_values[input.name].push(input.value);
                    } else {
                        form_values[input.name] = [form_values[input.name], input.value];
                    }
                } else {
                    if (input.value != '') {
                        form_values[input.name] = input.value;
                    }
                }
            });

            // Overwrite form_values array with values from the form tag
            // Necessary to handle field values generated server-side, since
            // using t-att- inside a snippet makes it non-editable !
            for (var key in this.$target.data()) {
                if (_.str.startsWith(key, 'form_field_')){
                    form_values[key.replace('form_field_', '')] = this.$target.data(key);
                }
            }

            // Post form and handle result
            ajax.post(this.$target.attr('action') + (this.$target.data('force_action')||this.$target.data('model_name')), form_values)
            .then(function(result_data) {
                let result_data_raw = result_data;
                result_data = $.parseJSON(result_data);
                if (result_data_raw.indexOf('tracking_code_new_complaint') != -1 || result_data_raw.indexOf('tracking_code_new_communication') != -1) {
                    // New behavior for new complaints and communications (modified EIS)
                    if (result_data_raw.indexOf('tracking_code_new_complaint') != -1) {
                        if(!result_data.id || result_data.tracking_code_new_complaint === null || result_data.tracking_code_new_complaint === '') {
                            self.update_status('error');
                            if (result_data.error_fields && result_data.error_fields.length) {
                                self.check_error_fields(result_data.error_fields);
                            }
                        } else {
                            let tracking_code_url = '/tracking-code?code=' + result_data.tracking_code_new_complaint
                            $(location).attr('href', tracking_code_url);
                            self.$target[0].reset();
                        }
                    }
                    if (result_data_raw.indexOf('tracking_code_new_communication') != -1) {
                        if(!result_data.id || result_data.tracking_code_new_communication === null || result_data.tracking_code_new_communication === '') {
                            self.update_status('error');
                            if (result_data.error_fields && result_data.error_fields.length) {
                                self.check_error_fields(result_data.error_fields);
                            }
                        } else {
                            // Pending
                            self.$target[0].reset();
                        }
                    }
                } else {
                    // Default behavior (original from website_form module -note of EIS-)
                    if(!result_data.id) {
                        // Failure, the server didn't return the created record ID
                        self.update_status('error');
                        if (result_data.error_fields && result_data.error_fields.length) {
                            // If the server return a list of bad fields, show these fields for users
                            self.check_error_fields(result_data.error_fields);
                        }
                    } else {
                        // Modified EIS
                        $(location).attr('href', '/page/complaints-channel');
                        // Success, redirect or update status
                        // var success_page = self.$target.attr('data-success_page');
                        // if(success_page) {
                        //     $(location).attr('href', success_page);
                        // }
                        // else {
                        //     self.update_status('success');
                        // }
                        // // Reset the form
                        // self.$target[0].reset();
                    }
                }
            })
            .fail(function(result_data){
            self.update_status('error');
            });
        },

    });

});