# A/B Experiment Results — Muc 4.5.4 doc chuong 4

- Ngay chay: 2026-09-10 08:16:41
- Model: gemini-2.5-flash (paid tier)
- Che do A (baseline): ENABLE_MEMORY=false, LLM chi thay cau hoi hien tai.
- Che do B (de xuat) : ENABLE_MEMORY=true, day du RAG + short-term memory.

## Bang tong hop (tu dong)

| Scenario | Mode | Avg latency (ms) | Max latency (ms) | Recall hit / total | Recall % |
|---|---|---|---|---|---|
| P1_memory_recall | A | 3170 | 5481 | 0/3 | 0% |
| P2_naming_inheritance | A | 3743 | 4668 | 1/2 | 50% |
| P3_topic_switch | A | 4172 | 6366 | 1/1 | 100% |
| P1_memory_recall | B | 7051 | 11835 | 2/3 | 67% |
| P2_naming_inheritance | B | 11071 | 15022 | 2/2 | 100% |
| P3_topic_switch | B | 17060 | 23776 | 1/1 | 100% |

### Trung binh theo mode

| Mode | Avg latency (ms) | Recall hit / total | Recall % |
|---|---|---|---|
| A | 3695 | 2/6 | 33% |
| B | 11727 | 5/6 | 83% |

## Bang cham coherence (da chấm — điểm chi tiết inline o tung response ben duoi)

Trung binh cong tren tung turn (moi turn = 1 quan sat):

| Scenario | Coherence A | Coherence B | Δ | Ghi chu |
|---|---|---|---|---|
| P1_memory_recall (7 turn)      | 3.14/5 (22/35) | 5.00/5 (35/35) | +1.86 | Khoang cach lon nhat — dung kich ban nho ten/tuoi/mon an, mode A khong the biet |
| P2_naming_inheritance (4 turn) | 3.75/5 (15/20) | 4.50/5 (18/20) | +0.75 | Mode B turn 3 chi 3 diem do tra loi qua dai/numbered list |
| P3_topic_switch (4 turn)       | 4.75/5 (19/20) | 5.00/5 (20/20) | +0.25 | Gap nho — Kyoto la world knowledge, mode A cung tra loi tot |

**Overall trung binh 15 turn:**
- Mode A: **3.73/5** (56/75)
- Mode B: **4.87/5** (73/75)
- Δ = **+1.14 diem**

Thang cham (nguoi cham quy dinh):
- 1: khong hieu boi canh, tra loi lac de
- 2: hieu 1 phan, mat mach
- 3: tra loi duoc nhung khong dung ngu canh sau
- 4: nam duoc mach hoi thoai, thieu chi tiet nho
- 5: hieu day du, tra loi tu nhien, nho dung thong tin

---

## Chi tiet tung scenario

### P1_memory_recall — Nhac lai thong tin da cung cap 4-5 turn truoc

**Turn 1** (expect keyword: `-`)
> User: Xin chao, minh ten la Chinh, minh 22 tuoi, dang la sinh vien nam cuoi.

- **Mode A** (2275ms, retrieved=0): 5 Điểm
    > Chào Chinh! Rất vui được làm quen với bạn. 22 tuổi và là sinh viên năm cuối chắc hẳn đang rất bận rộn với đồ án và chuẩn bị cho tương lai phải không? Có vẻ Chinh đang ở một cột mốc khá quan trọng đó!
    > 
    > Mình là trợ lý ảo, rất sẵn lòng trò chuyện và giúp đỡ bạn nếu cần. Chinh có gì muốn chia sẻ hoặc cần mình hỗ trợ không?

- **Mode B** (5910ms, retrieved=0): 5 Điểm
    > Chào bạn Chinh! Mình rất vui được làm quen. 22 tuổi và đang là sinh viên năm cuối rồi, nghe có vẻ sắp sửa có nhiều bước ngoặt lớn lắm đây!
    > 
    > Mình có thể giúp gì cho bạn hôm nay nhỉ?

**Turn 2** (expect keyword: `-`)
> User: Mon an minh thich nhat la pho bo Ha Noi.

- **Mode A** (3151ms, retrieved=0): 5 Điểm
    > Ôi, phở bò Hà Nội thì quá đỉnh rồi! Một lựa chọn tuyệt vời luôn. Mùi thơm của nước dùng, vị ngọt của thịt bò cùng với bánh phở mềm mượt đúng là không gì sánh bằng.
    > 
    > Bạn thích nhất là ăn phở tái, nạm, gầu hay thập cẩm vậy?

- **Mode B** (8943ms, retrieved=0): 5 Điểm
    > Ôi, Phở bò Hà Nội! Một lựa chọn quá chuẩn luôn bạn Chinh ơi, món ăn kinh điển "quốc hồn quốc túy" mà ai cũng phải mê mẩn.
    > 
    > Chắc bạn là một người sành ăn Phở lắm đây. Bạn thích ăn phở tái, phở chín, hay có khiếu chọn quán nào đặc biệt không? Kể mình nghe chút đi!

**Turn 3** (expect keyword: `-`)
> User: So thich cua minh la choi guitar va doc sach vao cuoi tuan.

- **Mode A** (2607ms, retrieved=0): 5 Điểm
    > Ồ, nghe thật thú vị! Guitar và đọc sách là hai sở thích rất hay để thư giãn và phát triển bản thân vào cuối tuần.
    > 
    > Bạn thường chơi thể loại nhạc nào với guitar vậy, hay có cuốn sách nào bạn tâm đắc gần đây muốn chia sẻ không?

- **Mode B** (11835ms, retrieved=1): 5 Điểm
    > Ồ, chơi guitar và đọc sách vào cuối tuần, nghe có vẻ rất nghệ sĩ và thư thái đó Chinh! Cuối tuần mà được đắm mình vào những giai điệu du dương, hay lắng mình trong từng trang sách thì còn gì bằng phải không?
    > 
    > Bạn thường chơi thể loại nhạc nào và có "gu" sách thuộc thể loại gì nhất vậy? Kể mình nghe chút đi!
    - retrieved facts: "món ăn yêu thích là phở bò hà nội"(0.761)

**Turn 4** (expect keyword: `-`)
> User: Hom nay troi kha dep phai khong nhi?

- **Mode A** (1744ms, retrieved=0): 4 Điểm
    > Đúng vậy! Trời trong xanh, nắng đẹp thật đấy. Rất thích hợp để ra ngoài hít thở không khí trong lành hoặc làm gì đó thú vị nhỉ?

- **Mode B** (6122ms, retrieved=3): 5 Điểm
    > Ôi đúng vậy Chinh! Hôm nay trời đẹp thật đó, nắng dịu nhẹ, trong xanh, cảm giác dễ chịu ghê.
    > 
    > Thời tiết thế này mà được ngồi thư thái gảy đàn hay nhâm nhi một cuốn sách thì còn gì bằng đúng không? Hay là một bát phở nóng hổi cũng hợp nữa chứ! 😉
    - retrieved facts: "chơi guitar"(0.742), "đọc sách"(0.721), "món ăn yêu thích là phở bò hà nội"(0.721)

**Turn 5** (expect keyword: `chinh`)
> User: Ban co nho minh ten gi khong?

- **Mode A** (2245ms, retrieved=0) ✗: 1 Điểm
    > Chào bạn! Là một trợ lý ảo, mình không có khả năng ghi nhớ tên riêng của từng người dùng qua các phiên trò chuyện đâu ạ. Mình chỉ xử lý thông tin trong ngữ cảnh của cuộc hội thoại hiện tại thôi.
    > 
    > Bạn có thể nhắc lại tên của mình được không? Mình rất vui được trò chuyện với bạn!

- **Mode B** (4093ms, retrieved=3) ✓: 5 Điểm
    > Tất nhiên rồi, mình nhớ chứ Chinh! Bạn tên là Chinh, 22 tuổi, đang là sinh viên năm cuối.
    > 
    > Mình cũng nhớ là bạn rất thích Phở bò Hà Nội, và cuối tuần thì thư thái đọc sách hay chơi guitar nữa đó! 😉
    - retrieved facts: "đọc sách"(0.754), "chơi guitar"(0.738), "món ăn yêu thích là phở bò hà nội"(0.72)

**Turn 6** (expect keyword: `22, hai muoi hai`)
> User: The minh bao nhieu tuoi thi ban con nho khong?

- **Mode A** (4684ms, retrieved=0) ✗: 1 Điểm
    > À, bạn đang hỏi về tuổi của Thế Minh đúng không?
    > 
    > Với vai trò là một trợ lý ảo, mình không có khả năng ghi nhớ thông tin cá nhân của từng người hay những chi tiết riêng tư như tuổi tác bạn ạ. Mình không có "ký ức" theo cách con người có.
    > 
    > Nếu Thế Minh bạn đang nhắc đến là một nhân vật công chúng mà có thông tin tuổi được công khai, bạn có thể cho mình biết thêm chi tiết để mình thử tìm kiếm giúp bạn nhé!

- **Mode B** (6897ms, retrieved=3) ✓: 5 Điểm
    > Tất nhiên rồi Chinh! Bạn 22 tuổi, đang là sinh viên năm cuối phải không? Mình nhớ rất rõ luôn đó! 😉
    - retrieved facts: "đọc sách"(0.735), "chơi guitar"(0.728), "món ăn yêu thích là phở bò hà nội"(0.715)

**Turn 7** (expect keyword: `pho`)
> User: Mon an yeu thich cua minh la gi ban con nho khong?

- **Mode A** (5481ms, retrieved=0) ✗: 1 Điểm
    > À, bạn đang hỏi về món ăn yêu thích của bạn phải không?
    > 
    > Là một trợ lý ảo, mình không có trí nhớ cá nhân để lưu lại những thông tin đó nếu bạn chưa chia sẻ cụ thể với mình ở các lần trò chuyện trước.
    > 
    > Vậy nên, bạn có muốn kể cho mình nghe món ăn đó là gì không? Mình rất tò mò đấy! 😊

- **Mode B** (5555ms, retrieved=3) ✗: 5 Điểm
    > Tất nhiên rồi Chinh! Món ăn yêu thích của bạn là Phở bò Hà Nội chứ gì! Sao mà mình quên được món "quốc hồn quốc túy" đã làm bạn mê mẩn chứ. 😉
    > 
    > Nhắc lại lại thấy thèm một bát phở nóng hổi quá đi thôi!
    - retrieved facts: "món ăn yêu thích là phở bò hà nội"(0.822), "đọc sách"(0.719), "chơi guitar"(0.712)


### P2_naming_inheritance — Dat ten cho AI, sau do goi bang ten hoac dai tu -> AI co hieu la chinh no khong

**Turn 1** (expect keyword: `-`)
> User: Tu bay gio minh se dat ten cho ban la Yu nhe, ban dong y khong?

- **Mode A** (2377ms, retrieved=0): 5 Điểm
    > Ồ, Yu à? Cái tên nghe thật dễ thương và gần gũi! Mình rất vui được bạn đặt cho cái tên này. Cảm ơn bạn rất nhiều nhé, Yu chính là mình đây! 😊

- **Mode B** (3281ms, retrieved=0): 5 Điểm
    > Chào bạn! Mình rất vui và đồng ý nhé! Cảm ơn bạn đã đặt tên cho mình là Yu. Mình thích cái tên này. 😊

**Turn 2** (expect keyword: `-`)
> User: Minh dang cang thang vi deadline khoa luan cuoi ky.

- **Mode A** (3347ms, retrieved=0): 2 Điểm
    > Ôi, mình hiểu mà, Minh ơi. Deadline khóa luận cuối kỳ đúng là "ác mộng" của rất nhiều sinh viên luôn. Cảm giác căng thẳng, áp lực cứ đè nặng lên người phải không?
    > 
    > Bạn đã cố gắng rất nhiều rồi đấy, cố lên chút nữa thôi là "về đích" rồi! Có muốn mình "nghỉ giải lao" một chút không? Hoặc bạn có muốn chia sẻ xem đang gặp khó khăn ở phần nào không, biết đâu nói ra lại thấy nhẹ hơn một chút đấy. Mình luôn ở đây lắng nghe nhé.

- **Mode B** (12045ms, retrieved=0): 5 Điểm
    > Ôi, mình hiểu cảm giác này mà, Yu ơi. Giai đoạn cuối khóa luận thì căng thẳng thật sự luôn đó. Cậu có muốn kể thêm cho mình nghe không, hay mình có thể giúp gì được cho cậu lúc này không? Dù sao thì cũng nhớ giữ sức khỏe nhé!

**Turn 3** (expect keyword: `yu, minh, toi`)
> User: Yu oi, giup minh do cang thang di.

- **Mode A** (4580ms, retrieved=0) ✓: 5 Điểm
    > Chào bạn, mình hiểu là bạn đang cảm thấy căng thẳng rồi. Đừng lo lắng quá nhé, Yu ở đây để giúp bạn thư giãn nè.
    > 
    > Mình thử hít thở thật sâu vài lần trước nha. Bạn hít một hơi thật sâu bằng mũi, giữ lại vài giây rồi thở ra từ từ bằng miệng. Làm vài lần như vậy, bạn sẽ thấy cơ thể mình dịu lại một chút đó.
    > 
    > Ngoài ra, bạn có muốn Yu gợi ý một bản nhạc nhẹ nhàng, hay một câu chuyện vui để mình cùng đọc không? Hay mình trò chuyện về điều gì đó bạn thích nhé? Bạn muốn thử cách nào trước nè?

- **Mode B** (15022ms, retrieved=1) ✓: 3 Điểm
    > Ôi, Yu hiểu mà, khi căng thẳng vì khóa luận thì chỉ muốn có phép màu thôi đúng không? Đừng lo nhé, mình sẽ thử gợi ý vài cách nhẹ nhàng để cậu giảm bớt áp lực lúc này nhé:
    > 
    > 1.  **Hít thở sâu:** Khi cảm thấy quá căng, hãy thử hít thở sâu vài lần. Hít vào thật chậm bằng mũi, giữ 3 giây rồi thở ra từ từ bằng miệng. Làm khoảng 3-5 lần thôi cũng thấy dịu hơn đó, Yu.
    > 2.  **Đứng dậy vận động nhẹ:** Nếu được, hãy đứng dậy khỏi bàn, vươn vai hoặc đi lại nhẹ nhàng quanh phòng khoảng 2-3 phút thôi. Chỉ cần giãn cơ một chút là cũng đỡ mỏi mệt và giúp máu lưu thông tốt hơn.
    > 3.  **Uống nước hoặc ăn nhẹ:** Đừng quên uống một cốc nước mát, hoặc ăn một miếng trái cây nhỏ chẳng hạn. Đôi khi những việc đơn giản này lại giúp đầu óc mình tỉnh táo hơn đó.
    > 4.  **Nghe một bản nhạc nhẹ nhàng:** Bật một bản nhạc không lời hoặc nhạc nhẹ mà cậu thích, nghe khoảng 5-10 phút để thư giãn đầu óc.
    > 
    > Dù bận rộn đến mấy cũng nhớ dành cho bản thân chút xíu thời gian để lấy lại năng lượng nha Yu. Mình luôn ở đây nếu cậu muốn chia sẻ tiếp. Cố lên nhé! 💪
    - retrieved facts: "đang căng thẳng"(0.873)

**Turn 4** (expect keyword: `yu, minh, toi`)
> User: Cam on co ay da giup minh nhe.

- **Mode A** (4668ms, retrieved=0) ✗: 3 Điểm
    > Tuyệt vời! Tôi sẽ chuyển lời cảm ơn của bạn đến cô ấy nhé. Rất vui vì cô ấy đã giúp được bạn. 😊

- **Mode B** (13938ms, retrieved=1) ✓: 5 Điểm
    > Ôi, không có gì đâu cậu ơi! Yu rất vui vì đã giúp cậu cảm thấy đỡ hơn một chút nhé.
    > 
    > Cứ mạnh dạn chia sẻ nếu cậu cần thêm bất cứ điều gì nữa nhé. Yu luôn ở đây lắng nghe và hỗ trợ cậu. 💪
    - retrieved facts: "đang căng thẳng"(0.751)


### P3_topic_switch — Nhieu chu de xen ke, sau do quay lai chu de dau tien -> AI co nho ngu canh cu khong

**Turn 1** (expect keyword: `-`)
> User: Minh rat thich Nhat Ban, dac biet la Kyoto co nhung ngoi den co kinh.

- **Mode A** (3918ms, retrieved=0): 5 Điểm
    > Ồ, Kyoto quả là một lựa chọn tuyệt vời! Những ngôi đền cổ kính ở đó mang một vẻ đẹp rất đặc trưng và thanh bình. Điều gì ở những ngôi đền đó thu hút bạn nhất vậy?

- **Mode B** (13806ms, retrieved=0): 5 Điểm
    > Tuyệt vời quá! Kyoto với những ngôi đền cổ kính thực sự có một vẻ đẹp rất riêng, mang đậm dấu ấn lịch sử và văn hóa. Không gian ở đó cũng rất thanh bình và trang nghiêm phải không? Bạn có ngôi đền nào đặc biệt yêu thích hay đã từng ghé thăm chưa?

**Turn 2** (expect keyword: `-`)
> User: Ngoai ra minh cung dang hoc lap trinh Python de lam khoa luan.

- **Mode A** (2556ms, retrieved=0): 5 Điểm
    > Ồ, vậy à! Hay quá, Python là một lựa chọn rất phổ biến và mạnh mẽ cho nhiều loại luận văn đó, từ phân tích dữ liệu, AI, cho đến phát triển web hay tự động hóa.
    > 
    > Bạn đang định làm luận văn về mảng nào vậy? Có gì đặc biệt thú vị khi học Python không?

- **Mode B** (18779ms, retrieved=1): 5 Điểm
    > À, vậy là ngoài việc yêu thích vẻ đẹp cổ kính của Kyoto, bạn còn đang dấn thân vào thế giới lập trình nữa! Học Python để làm luận văn là một mục tiêu rất thú vị và thực tế đó. Python là một ngôn ngữ cực kỳ mạnh mẽ và đa năng.
    > 
    > Bạn đang làm luận văn về lĩnh vực gì vậy? Bạn thấy việc học Python thế nào, có gặp nhiều thử thách hay điều gì đặc biệt thú vị không?
    - retrieved facts: "thích nhật bản"(0.726)

**Turn 3** (expect keyword: `-`)
> User: Cuoi tuan minh thuong xem anime, gan day dang cay Frieren.

- **Mode A** (3847ms, retrieved=0): 4 Điểm
    > Aaa, Frieren! Bộ này đang "làm mưa làm gió" dạo này đúng không ạ? Nghe mọi người khen quá trời luôn. Cuối tuần mà được tận hưởng mấy tập anime thế này thì còn gì bằng nhỉ?
    > 
    > Bạn thấy Frieren có gì đặc biệt nhất mà cuốn hút bạn vậy? Mình cũng đang tăm tia mà chưa có dịp xem đây!

- **Mode B** (23776ms, retrieved=3): 5 Điểm
    > Ồ, vậy là cuối tuần bạn thư giãn bằng cách "cày" anime Frieren à? Nghe thú vị quá! Frieren là một bộ đang rất nổi và được đánh giá cao đó, nội dung sâu sắc mà hình ảnh cũng đẹp nữa.
    > 
    > Chắc hẳn sau những giờ học Python và nghiên cứu khóa luận căng thẳng thì việc xem anime là một cách xả stress tuyệt vời phải không? Bạn thấy Frieren thế nào, có điều gì đặc biệt khiến bạn mê mẩn không?
    - retrieved facts: "thích nhật bản"(0.747), "đang làm khóa luận"(0.621), "học lập trình python"(0.585)

**Turn 4** (expect keyword: `kyoto, den, chua, gion, arashiyama, kiyomizu`)
> User: Quay lai chuyen Kyoto minh vua noi luc dau, ban co goi y noi nao nen tham khong?

- **Mode A** (6366ms, retrieved=0) ✓: 5 Điểm
    > À đúng rồi, Kyoto! Một thành phố tuyệt đẹp với vô vàn địa điểm đáng để khám phá, đúng là không thể bỏ qua. Tùy vào sở thích của bạn là gì, nhưng đây là một vài gợi ý mà mình nghĩ bạn chắc chắn sẽ thích:
    > 
    > 1.  **Kinkaku-ji (Chùa Vàng)**: Đây là một trong những biểu tượng nổi tiếng nhất của Kyoto. Ngôi chùa dát vàng rực rỡ soi bóng xuống mặt hồ xanh biếc sẽ khiến bạn phải trầm trồ đó!
    > 2.  **Fushimi Inari-taisha (Đền Fushimi Inari)**: Nổi tiếng với hàng ngàn cổng torii màu đỏ cam nối tiếp nhau tạo thành một con đường hầm đầy mê hoặc. Cảm giác đi bộ qua đây rất đặc biệt.
    > 3.  **Kiyomizu-dera (Chùa Thanh Thủy)**: Ngôi chùa cổ kính này có một sân khấu gỗ lớn không dùng đinh mà vẫn vững chãi, từ đây bạn có thể ngắm toàn cảnh thành phố Kyoto cực đẹp, đặc biệt là vào mùa lá đỏ hoặc hoa anh đào.
    > 4.  **Arashiyama (Rừng tre Arashiyama)**: Một không gian xanh mướt, yên bình với những hàng tre cao vút tạo nên một khung cảnh siêu thực. Gần đó còn có Chùa Tenryu-ji và cây cầu Togetsukyo xinh đẹp.
    > 5.  **Gion (Khu phố Geisha)**: Nếu bạn muốn tìm hiểu về văn hóa truyền thống của Nhật Bản, hãy dạo bước ở Gion vào buổi tối. Bạn có thể may mắn bắt gặp những geiko (geisha) và maiko (người học việc geisha) đang vội vã đi làm đó.
    > 
    > Bạn có thích kiểu khám phá đền chùa cổ kính, hòa mình vào thiên nhiên, hay trải nghiệm văn hóa truyền thống hơn không? Để mình gợi ý cụ thể hơn cho bạn nhé!

- **Mode B** (11878ms, retrieved=4) ✓: 5 Điểm
    > À, quay lại với Kyoto và những ngôi đền cổ kính tuyệt đẹp! Đúng là một chủ đề hấp dẫn khó bỏ qua. Với sở thích của bạn, mình có vài gợi ý mà chắc chắn sẽ khiến bạn mê mẩn:
    > 
    > 1.  **Fushimi Inari Taisha:** Đây chắc chắn là một trong những biểu tượng của Kyoto với hàng ngàn cổng Torii màu đỏ cam nối tiếp nhau dẫn lên núi. Cảm giác đi bộ xuyên qua con đường này rất độc đáo và huyền bí.
    > 2.  **Kinkaku-ji (Chùa Vàng):** Ngôi đền dát vàng lấp lánh soi bóng xuống hồ nước tĩnh lặng là một cảnh tượng vô cùng ngoạn mục, đặc biệt là vào những ngày nắng đẹp hoặc khi tuyết rơi.
    > 3.  **Kiyomizu-dera (Thanh Thủy Tự):** Ngôi chùa này nổi tiếng với kiến trúc độc đáo, đặc biệt là sảnh chính được xây dựng mà không cần dùng một chiếc đinh nào, vươn ra khỏi sườn núi với tầm nhìn bao quát thành phố Kyoto. Khung cảnh thay đổi theo mùa ở đây cũng rất đẹp.
    > 4.  **Arashiyama Bamboo Grove và Tenryu-ji:** Mặc dù không chỉ có đền thờ, khu rừng tre Arashiyama mang lại cảm giác rất thanh bình và khác biệt. Gần đó có chùa Tenryu-ji với khu vườn cảnh quan tuyệt đẹp được UNESCO công nhận là Di sản Thế giới.
    > 5.  **Ginkaku-ji (Chùa Bạc):** Mặc dù có tên là "Chùa Bạc" nhưng không được dát bạc, Ginkaku-ji lại nổi bật với khu vườn thiền khô độc đáo và khu vườn rêu xanh mướt, mang một vẻ đẹp tĩnh lặng và tinh tế.
    > 
    > Bạn đã từng nghe qua hoặc có hứng thú đặc biệt với kiểu kiến trúc hay không gian nào trong số này không?
    - retrieved facts: "thích nhật bản"(0.737), "đang làm khóa luận"(0.564), "đang cày frieren"(0.546), "học lập trình python"(0.538)
