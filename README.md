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
<summary><b>操作説明</b></summary>
※Unityのみでも動作しますが，本来はNFCリーダーをつなげてかざすと残高に応じたモンスターが召喚され，Printerも接続するとその後，そのモンスターのカードが印刷されます！

**キー入力**
- `0`：疑似体験　ランダムでモンスターが表示されます！（HP・MPカウント`On/Off`切り替えられます）
- `1`~`7`：その数字に合わせたモンスターが表示されます（それぞれ1回カウント）
- `8`：シークレットモンスター(？)です！
- `Ctrl` + `Shift` + `R`：カウントがリセットされます
- `N`：エンディング画面です（BGMはないです）

**Unity`GameManager(MonsterManager)`の設定**

- `Atk・Def・Spd Phrases`：こうげき力，ぼうぎょ力，すばやさのランダムのフレーズをそれぞれ設定できます

～目標設定～
- `Total Hp Goal`：HPバーの最大値です（合計金額）
- `Total Mp Goal`：Mpバーの最大値です（遊んでくれた回数（同じUIDは除く））

～演出維持設定～
- `Min Display Seconds`：モンスターを表示させる秒数です

～デバッグ設定～
- `Rare Spawn Chance`：`0`キーを入力した際にシークレットモンスターが出現する確率です
- `Count Debug Zero`：`0`キーを入力した際にHP・MPカウントするかを切り替えられます（`On`：カウントする）
</details>

<details>
<summary><b>実際の様子✨</b></summary>

<p align="center">
<img alt="WaitingScreen" src="https://github.com/user-attachments/assets/051ad010-b630-4f19-925a-a67f8ff1ff96" width="25%">
 &nbsp;&nbsp;
<img alt="ペカ&ピカ" src="https://github.com/nairo-ngkr/2026Omiyafes-OrenoZandaka/blob/main/PlayPhotos%26Video/%E3%83%9A%E3%82%AB%26%E3%83%94%E3%82%AB.jpg" width="45%">
 &nbsp;&nbsp;
<img alt="ごんた" src="https://github.com/nairo-ngkr/2026Omiyafes-OrenoZandaka/blob/main/PlayPhotos%26Video/%E3%81%94%E3%82%93%E3%81%9F.jpg" width="25%">
 
<img alt="カード" src="https://github.com/nairo-ngkr/2026Omiyafes-OrenoZandaka/blob/main/PlayPhotos%26Video/%E3%82%AB%E3%83%BC%E3%83%89.jpg" width="45%">
 &nbsp;&nbsp;
<img alt="Ending(合計)" src="https://github.com/nairo-ngkr/2026Omiyafes-OrenoZandaka/blob/main/PlayPhotos%26Video/EndingResult.png" width="50%">
</p>
 
> <details>
> <summary><b>魔法陣の動画</b></summary>
> <div><video controls src="https://github.com/user-attachments/assets/7cd9c98b-afe8-4765-8e7d-1ccccefd9a70" muted="false"></video></div>
> </details>

</details>
