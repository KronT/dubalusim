/**
 * HMAC-SHA1 exports
 */
if ( typeof hmac_sha1_constructor !== 'undefined' )
{
    function hmac_sha1_bytes ( data, password ) {
        if ( data === undefined ) throw new SyntaxError("data required");
        if ( password === undefined ) throw new SyntaxError("password required");
        return get_hmac_sha1_instance().reset( { password: password } ).process(data).finish().result;
    }

    function hmac_sha1_hex ( data, password ) {
        var result = hmac_sha1_bytes( data, password );
        return bytes_to_hex(result);
    }

    function hmac_sha1_base64 ( data, password ) {
        var result = hmac_sha1_bytes( data, password );
        return bytes_to_base64(result);
    }

    exports.HMAC =
    exports.HMAC_SHA1 = {
        bytes: hmac_sha1_bytes,
        hex: hmac_sha1_hex,
        base64: hmac_sha1_base64
    };
}

/**
 * HMAC-SHA256 exports
 */
if ( typeof hmac_sha256_constructor !== 'undefined' )
{
    function hmac_sha256_bytes ( data, password ) {
        if ( data === undefined ) throw new SyntaxError("data required");
        if ( password === undefined ) throw new SyntaxError("password required");
        return get_hmac_sha256_instance().reset( { password: password } ).process(data).finish().result;
    }

    function hmac_sha256_hex ( data, password ) {
        var result = hmac_sha256_bytes( data, password );
        return bytes_to_hex(result);
    }

    function hmac_sha256_base64 ( data, password ) {
        var result = hmac_sha256_bytes( data, password );
        return bytes_to_base64(result);
    }

    exports.HMAC_SHA256 = {
        bytes: hmac_sha256_bytes,
        hex: hmac_sha256_hex,
        base64: hmac_sha256_base64
    };
}

/**
 * HMAC-SHA512 exports
 */
if ( typeof hmac_sha512_constructor !== 'undefined' )
{
    function hmac_sha512_bytes ( data, password ) {
        if ( data === undefined ) throw new SyntaxError("data required");
        if ( password === undefined ) throw new SyntaxError("password required");
        return get_hmac_sha512_instance().reset( { password: password } ).process(data).finish().result;
    }

    function hmac_sha512_hex ( data, password ) {
        var result = hmac_sha512_bytes( data, password );
        return bytes_to_hex(result);
    }

    function hmac_sha512_base64 ( data, password ) {
        var result = hmac_sha512_bytes( data, password );
        return bytes_to_base64(result);
    }

    exports.HMAC_SHA512 = {
        bytes: hmac_sha512_bytes,
        hex: hmac_sha512_hex,
        base64: hmac_sha512_base64
    };
}
