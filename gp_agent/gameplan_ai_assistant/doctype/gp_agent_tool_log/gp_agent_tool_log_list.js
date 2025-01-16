frappe.listview_settings['GP Agent Tool Log'] = {
    get_indicator: function(doc) {
        return [__(doc.status), {
            'Queued': 'blue',
            'Processing': 'orange',
            'Completed': 'green',
            'Failed': 'red',
            'Error': 'red'
        }[doc.status], 'status,=,' + doc.status];
    },
    hide_name_column: true,
    hide_name_filter: true
}; 