'use strict';
(function($) {
    $(document).ready(function() {
        let hasVariantsCheckbox = $('#id_has_variants');
        let singleProductFields = $('.single-product-fields');
        let variantsInline = $('#productvariant_set-group');

        function toggleVariantFields() {
            if (hasVariantsCheckbox.prop('checked')) {
                // Product HAS variants
                singleProductFields.hide();
                variantsInline.show();
            } else {
                // Product does NOT have variants
                singleProductFields.show();
                variantsInline.hide();
            }
        }

        // Run on page load
        toggleVariantFields();

        // Run on checkbox change
        hasVariantsCheckbox.on('change', toggleVariantFields);
    });
})(django.jQuery);
