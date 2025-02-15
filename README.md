# ZIP to Markdown 

ZIP to Markdown es una aplicación web, que recibe un zip con un proyecto, y te devuelve un archivo markdown con la documentación del proyecto en cuestión realizada automáticamente. 

El front se encuentra realizado en html, css y javascript, y se encuentra disponible en la siguiente url: https://zip-to-markdown.hectorgv00.online/

Si pulsamos el botón de choose a zip file, o le arrastramos el zip y le damos a generar, el front hace una llamada a la otra parte de la aplicación, el back, que está hecho en python y corre en un servidor de flask, que recibe la llamada, revisa todos los archivos y genera la documentación en markdown.
