core/ckeditor.js, remove or comment:
--- a/core/ckeditor.js.orig
+++ b/core/ckeditor.js
@@ -143,7 +143,7 @@ CKEDITOR.on( 'instanceDestroyed', function() {
 } );

 // Load the bootstrap script.
-CKEDITOR.loader.load( '_bootstrap' ); // %REMOVE_LINE%
+// CKEDITOR.loader.load( '_bootstrap' ); // %REMOVE_LINE%

 // Tri-state constants.
 /**


in core/skin.js, modify getCssPath to use CSS from CKEDITOR_CSS,
and make sure those are defined in base.html:
--- a/core/skin.js.orig
+++ b/core/skin.js
@@ -155,13 +155,14 @@
 				}
 			}
 		}
-		return CKEDITOR.getUrl( getConfigPath() + part + '.css' );
+		return CKEDITOR_CSS[part] && CKEDITOR.getUrl( CKEDITOR_CSS[part] );
 	}

 	function loadCss( part, callback ) {
 		// Avoid reload.
 		if ( !cssLoaded[ part ] ) {
-			CKEDITOR.document.appendStyleSheet( getCssPath( part ) );
+			var url = getCssPath( part );
+			if ( url ) CKEDITOR.document.appendStyleSheet( url );
 			cssLoaded[ part ] = 1;
 		}
