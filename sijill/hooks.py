app_name = "sijill"
app_title = "Sijill"
app_publisher = "SDCE"
app_description = "Financial and operational reports for ERPNext, starting with the Saudi VAT return"
app_email = "info@sdce.sa"
app_license = "gpl-3.0"

required_apps = ["erpnext"]

# NOTE: app_logo_url is intentionally NOT set: on a shared site the last installed app's
# app_logo_url replaces the navbar / login logo for every user. The Sijill logo is carried by the
# Desktop Icon (sijill/desktop_icon/sijill.json) and add_to_apps_screen.
add_to_apps_screen = [
	{
		"name": "sijill",
		"logo": "/assets/sijill/images/sijill-logo.svg",
		"title": "Sijill",
		"route": "/desk/sijill",
		"has_permission": "sijill.utils.has_app_permission",
	}
]
