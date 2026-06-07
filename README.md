<h1 align="center">2026年大宮祭（ShibaLab）</h1>

 ![TitleLogo](https://github.com/nairo-ngkr/2026Omiyafes-OrenoZandaka/blob/main/OrenoZandaka/Assets/Images/2026%E5%A4%A7%E5%AE%AE%E7%A5%AD%E3%83%AD%E3%82%B4-4.png)

<h2 align="center">
俺のICカードの残高が、異世界では最強の魔力だった件<br>
～残高124円で魔王を倒しに行けるわけがない～
</h2>

2026年大宮祭で展示した作品です．（反省会用でエンディング画面を追加したバージョンまで載せています）

### 作品概要
魔法陣に「交通系ICカード」をかざすと，そのカードに秘められた魔力（残高）に応じてモンスターが召喚され，仲間にすることができます！

<details>
<summary>操作説明</summary>
※Unityのみでも動作しますが，本来はNFCリーダーをつなげてかざすと残高に応じたモンスターが召喚され，Printerも接続するとその後，そのモンスターのカードが印刷されます！

**キー入力**
- 0：疑似体験　ランダムでモンスターが表示されます！（カウントOn・Off切り替えられます）
- 1~7：その数字に合わせたモンスターが表示されます（それぞれ1回カウント）
- 8：シークレットモンスター(？)です！
- Ctrl + Shift + R：カウントがリセットされます
- N：エンディング画面です（BGMはないです）

**Managerの設定**

- Atk・Def・Spd Phrases：こうげき力，ぼうぎょ力，すばやさのランダムのフレーズをそれぞれ設定できます

～目標設定～
- Total Hp Goal：HPバーの最大値です（合計金額）
- Total Mp Goal：Mpバーの最大値です（遊んでくれた回数（同じUIDは除く））

～演出維持設定～
- Min Display Seconds：モンスターを表示させる秒数です

～デバッグ設定～
- Rare Spawn Chance：0キーを入力した際にシークレットモンスターが出現する確率です
- Count Debug Zero：0キーを入力した際にHP・MPカウントするかを切り替えられます（On：カウントする）
</details>
