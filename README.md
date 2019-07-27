
## TLS 1.3 フルスクラッチ入門

TLS 1.3 をフルスクラッチするために役立つことを書きたい。
最終的には「n日でできる! TLS1.3自作入門」みたいな形にしたい。

モチベーション：

- TLS 1.3 を Python で実装できる
  - 鍵共有の仕組みや安全性が理解できる
  - 認証付き暗号が理解できる
  - 公開鍵基盤の仕組みが理解できる
- 以下はおまけ的な要素
  - RFCの読み方
  - SSL/TLS の歴史や攻撃手法

目次：

- curlによる TLS 1.3 のテスト
- Pythonでソケット通信
- プロトコルのデータ構造をオブジェクト化する (ClientHello, ServerHello など)
- データ構造とバイト列の相互変換
- DH鍵共有
- 暗号化
  - AES_128_GCM
  - AES_256_GCM
  - CHACHA20_POLY1305


### 参考文献

- [RFC 8446 -- The Transport Layer Security (TLS) Protocol Version 1.3](https://tools.ietf.org/html/rfc8446)
- [SSL and TLS Deployment Best Practices](https://github.com/ssllabs/research/wiki/SSL-and-TLS-Deployment-Best-Practices)
