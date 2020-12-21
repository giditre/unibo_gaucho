/* 5g MEC Related */
var _updateResult = function(data) {
	$( "#result" ).text(
		data
	)
}

var _clear_result = function() {
	_updateResult("");
}

var _get_query = function(endpoint) {
	$.get(endpoint).done(_updateResult);
}

var hello = function() {
	_get_query("hello");
}

var bye = function() {
	_clear_result();
}

var get_configuration = function() {
	$.get("_configuration").done( function (data_s) {
		data = JSON.parse(data_s)
		console.log("%o", data)
		Object.keys(data).forEach((key) => {
			if (typeof(data[key]) === 'string') {
				$( `#${key}` ).val(
					data[key]
				)
			} else {
				$( `#${key}` ).val(
					JSON.stringify(data[key], null, 4)
				)
			}
		})
	})
}

var sum = function() {
	data = {};
	[ "input1", "input2" ].forEach((k) => {
		data[k] = $( `#${k}` ).val()
	})

	// text_area_keys = ["service_data"];
	// // Text areas input
	// text_area_keys.forEach((key) => {
	// 	data[key] = JSON.parse($( `#${key}` ).val())
	// })

	$.ajax({
		url:'sum',
		type:'POST',
		data: JSON.stringify(data),
		contentType:"application/json; charset=utf-8",
		dataType:"json",
		success: function(r) {
      _updateResult(r)
    }
	})
}

var qrcode = function() {
	string = {};
	[ "string" ].forEach((k) => {
		string[k] = $( `#${k}` ).val()
	})
	qrObj = new Object();
  qrObj.data = string["string"];
  $("button").click(function(){
    $("div").text($.param(personObj));
  });
}

// function executed periodically
// setInterval(function() {
// 	$.get("_get_application_notice").done( function(data) {
// 		if (data === 'True') {
// 			$( "#service_ready_led" ).css(
// 				"background-color",
// 				"green"
// 			)
// 		}
// 	});
// }, 1000)

var activeMenu = 'hello'

/* UI related */
var activate_menu = function(menu) {
	$( `#${activeMenu}` ).removeClass('d-block')
	$( `#${activeMenu}` ).addClass('d-none')
	$( `#nav${activeMenu}` ).removeClass('active')
	$( `#${menu}` ).removeClass('d-none')
	$( `#${menu}` ).addClass('d-block')
	$( `#nav${menu}` ).addClass('active')

	activeMenu = menu
}
