/*
 * Riot Mobile (League Connect) SSL unpinning for Frida.
 * Covers BOTH the Java/Kotlin TLS stack AND native BoringSSL pinning used by
 * Riot's foundation SDK (libriotgamesapi / bundled boringssl).
 *
 * Usage (rooted device w/ frida-server, or HTTP Toolkit's injected Frida):
 *   frida -U -f com.riotgames.mobile.leagueconnect -l tools/frida_ssl_unpin.js
 * (use -f to spawn so native libs are hooked before they load)
 *
 */

'use strict';

function hookJava() {
  Java.perform(function () {
    const tries = [];

    // 1) X509TrustManager / TrustManagerImpl (AOSP, Conscrypt)
    try {
      const TMImpl = Java.use('com.android.org.conscrypt.TrustManagerImpl');
      TMImpl.checkTrustedRecursive.implementation = function () {
        return Java.use('java.util.ArrayList').$new();
      };
      tries.push('TrustManagerImpl.checkTrustedRecursive');
    } catch (e) {}
    try {
      const TMImpl = Java.use('com.android.org.conscrypt.TrustManagerImpl');
      TMImpl.verifyChain.implementation = function (untrustedChain) {
        return untrustedChain;
      };
      tries.push('TrustManagerImpl.verifyChain');
    } catch (e) {}

    // 2) Custom TrustManagers via SSLContext.init
    try {
      const SSLContext = Java.use('javax.net.ssl.SSLContext');
      const TrustManager = Java.registerClass({
        name: 'org.frida.TrustAll',
        implements: [Java.use('javax.net.ssl.X509TrustManager')],
        methods: {
          checkClientTrusted: function () {},
          checkServerTrusted: function () {},
          getAcceptedIssuers: function () { return []; },
        },
      });
      const init = SSLContext.init.overload(
        '[Ljavax.net.ssl.KeyManager;', '[Ljavax.net.ssl.TrustManager;',
        'java.security.SecureRandom');
      init.implementation = function (km, tm, sr) {
        init.call(this, km, [TrustManager.$new()], sr);
      };
      tries.push('SSLContext.init');
    } catch (e) {}

    // 3) OkHttp CertificatePinner
    try {
      const CP = Java.use('okhttp3.CertificatePinner');
      CP.check.overload('java.lang.String', 'java.util.List').implementation = function () {};
      tries.push('okhttp3.CertificatePinner.check(List)');
    } catch (e) {}
    try {
      const CP = Java.use('okhttp3.CertificatePinner');
      CP.check$okhttp.implementation = function () {};
      tries.push('okhttp3.CertificatePinner.check$okhttp');
    } catch (e) {}

    // 4) HostnameVerifier
    try {
      const HUC = Java.use('javax.net.ssl.HttpsURLConnection');
      HUC.setDefaultHostnameVerifier.implementation = function () {};
      HUC.setHostnameVerifier.implementation = function () {};
      tries.push('HttpsURLConnection HostnameVerifier');
    } catch (e) {}

    // 5) Conscrypt platform / TrustRootIndex
    try {
      const Platform = Java.use('okhttp3.internal.platform.Platform');
      Platform.trustManager.implementation = function () { return null; };
      tries.push('okhttp3 Platform.trustManager');
    } catch (e) {}

    // 6) WebView (the login webview)
    try {
      const WVC = Java.use('android.webkit.WebViewClient');
      WVC.onReceivedSslError.implementation = function (view, handler, error) {
        handler.proceed();
      };
      tries.push('WebViewClient.onReceivedSslError');
    } catch (e) {}

    console.log('[java] hooked: ' + (tries.join(', ') || 'none'));
  });
}

function hookNativeBoringSSL() {
  const targets = [];

  function patchModule(mod) {
    // SSL_set_custom_verify / SSL_CTX_set_custom_verify: force the callback to
    // return SSL_VERIFY_OK (0). The callback is the 3rd arg.
    ['SSL_CTX_set_custom_verify', 'SSL_set_custom_verify'].forEach(function (sym) {
      const addr = Module.findExportByName(mod.name, sym);
      if (!addr) return;
      try {
        Interceptor.attach(addr, {
          onEnter: function (args) {
            // replace the verify callback (args[2]) with one returning ssl_verify_ok(0)
            const cb = new NativeCallback(function () { return 0; }, 'int', ['pointer', 'pointer']);
            args[2] = cb;
            this._patched = true;
          },
        });
        targets.push(mod.name + '!' + sym);
      } catch (e) {}
    });

    // Older API: SSL_CTX_set_verify with a callback; and the chain verifier.
    ['SSL_get_verify_result'].forEach(function (sym) {
      const addr = Module.findExportByName(mod.name, sym);
      if (!addr) return;
      try {
        Interceptor.replace(addr, new NativeCallback(function () {
          return 0; // X509_V_OK
        }, 'long', ['pointer']));
        targets.push(mod.name + '!' + sym + ' (replaced)');
      } catch (e) {}
    });
  }

  // Scan loaded modules for ssl/crypto/riot native libs.
  Process.enumerateModules().forEach(function (m) {
    const n = m.name.toLowerCase();
    if (n.indexOf('ssl') !== -1 || n.indexOf('crypto') !== -1 ||
        n.indexOf('boringssl') !== -1 || n.indexOf('conscrypt') !== -1 ||
        n.indexOf('riot') !== -1 || n.indexOf('flutter') !== -1) {
      patchModule(m);
    }
  });

  console.log('[native] patched: ' + (targets.join(', ') || 'none found yet'));

  // Re-scan as libs load lazily (Riot SDK loads its native lib after start).
  try {
    const dlopen = Module.findExportByName(null, 'android_dlopen_ext') ||
                   Module.findExportByName(null, 'dlopen');
    if (dlopen) {
      Interceptor.attach(dlopen, {
        onEnter: function (args) { this.path = args[0].readUtf8String(); },
        onLeave: function () {
          if (!this.path) return;
          const low = this.path.toLowerCase();
          if (low.indexOf('ssl') !== -1 || low.indexOf('crypto') !== -1 ||
              low.indexOf('riot') !== -1 || low.indexOf('boringssl') !== -1) {
            const m = Process.findModuleByName(this.path.split('/').pop());
            if (m) { patchModule(m); console.log('[native] late-patched ' + m.name); }
          }
        },
      });
    }
  } catch (e) {}
}

setImmediate(function () {
  try { hookJava(); } catch (e) { console.log('[java] err ' + e); }
  try { hookNativeBoringSSL(); } catch (e) { console.log('[native] err ' + e); }
  console.log('[*] SSL unpinning installed.');
});
