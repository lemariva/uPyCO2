from waitress import serve
import restapi

serve(restapi.app, host='0.0.0.0', port=8000)