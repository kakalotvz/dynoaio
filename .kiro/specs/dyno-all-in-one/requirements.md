# Requirements Document

## Introduction

Dyno All In One là một ứng dụng launcher trên Windows, tổng hợp tất cả các phần mềm dyno xe đua (Redleo, Apitech, Ate, BRT, Uma, ...) vào một giao diện duy nhất. Người dùng có thể duyệt ứng dụng theo tên, chọn phiên bản và khởi chạy hoặc cài đặt chỉ với vài cú nhấp chuột. Ứng dụng hỗ trợ cả phần mềm portable (chạy thẳng) và phần mềm cần cài đặt (setup), tự động nhận dạng loại và xử lý tương ứng.

## Glossary

- **Launcher**: Ứng dụng Dyno All In One — giao diện chính tổng hợp các phần mềm dyno.
- **App_Card**: Nút/thẻ đại diện cho một ứng dụng dyno trên màn hình chính.
- **Version_Card**: Nút/thẻ đại diện cho một phiên bản cụ thể của ứng dụng dyno.
- **App_Directory**: Thư mục gốc chứa tất cả ứng dụng, có cấu trúc `root/Apps/<tên ứng dụng>/<phiên bản>/`.
- **Setup_File**: File cài đặt có chứa chuỗi "setup" trong tên (ví dụ: `Apitech_setup.msi`, `BRT_setup.exe`).
- **Portable_App**: Ứng dụng không có Setup_File trong thư mục phiên bản — chạy trực tiếp file `.exe`.
- **Installable_App**: Ứng dụng có Setup_File trong thư mục phiên bản — cần cài đặt trước khi chạy.
- **Silent_Install**: Quá trình cài đặt tự động không hiển thị wizard, chạy ngầm.
- **Install_Path_Resolver**: Thành phần tự động xác định đường dẫn cài đặt của ứng dụng sau khi cài xong.
- **Theme_Config**: File cấu hình giao diện riêng biệt, cho phép tùy chỉnh màu sắc, font chữ, logo.

---

## Requirements

### Requirement 1: Màn hình chính — Danh sách ứng dụng

**User Story:** Là người dùng, tôi muốn thấy danh sách tất cả ứng dụng dyno trên màn hình chính, để tôi có thể chọn ứng dụng cần dùng nhanh chóng.

#### Acceptance Criteria

1. WHEN Launcher khởi động, THE Launcher SHALL quét thư mục `Apps/` và hiển thị một App_Card cho mỗi thư mục con tìm thấy.
2. THE Launcher SHALL hiển thị tên ứng dụng trên mỗi App_Card lấy từ tên thư mục tương ứng.
3. IF thư mục `Apps/` không tồn tại hoặc rỗng, THEN THE Launcher SHALL hiển thị thông báo "Không tìm thấy ứng dụng nào".
4. WHEN người dùng nhấn vào một App_Card, THE Launcher SHALL chuyển sang màn hình danh sách phiên bản của ứng dụng đó.

---

### Requirement 2: Màn hình phiên bản — Danh sách phiên bản

**User Story:** Là người dùng, tôi muốn xem tất cả phiên bản có sẵn của một ứng dụng, để tôi chọn đúng phiên bản cần dùng.

#### Acceptance Criteria

1. WHEN người dùng nhấn vào một App_Card, THE Launcher SHALL quét thư mục con của ứng dụng đó và hiển thị một Version_Card cho mỗi phiên bản tìm thấy.
2. THE Launcher SHALL hiển thị tên phiên bản trên mỗi Version_Card lấy từ tên thư mục phiên bản.
3. IF thư mục ứng dụng không chứa thư mục phiên bản nào, THEN THE Launcher SHALL hiển thị thông báo "Không có phiên bản nào".
4. THE Launcher SHALL hiển thị nút "Quay lại" để người dùng trở về màn hình chính.

---

### Requirement 3: Nhận dạng loại ứng dụng

**User Story:** Là người dùng, tôi muốn ứng dụng tự nhận biết phần mềm nào cần cài đặt và phần mềm nào chạy thẳng, để tôi không cần phân biệt thủ công.

#### Acceptance Criteria

1. WHEN người dùng nhấn vào một Version_Card, THE Launcher SHALL kiểm tra thư mục phiên bản đó để xác định loại ứng dụng.
2. IF thư mục phiên bản chứa file `.exe` hoặc `.msi` có chuỗi "setup" trong tên file (không phân biệt hoa thường), THEN THE Launcher SHALL phân loại phiên bản đó là Installable_App.
3. IF thư mục phiên bản không chứa file nào có chuỗi "setup" trong tên, THEN THE Launcher SHALL phân loại phiên bản đó là Portable_App.

---

### Requirement 4: Chạy ứng dụng Portable

**User Story:** Là người dùng, tôi muốn nhấn vào phiên bản portable và ứng dụng chạy ngay, để tiết kiệm thời gian.

#### Acceptance Criteria

1. WHEN người dùng nhấn vào Version_Card của một Portable_App, THE Launcher SHALL tìm file `.exe` đầu tiên trong thư mục phiên bản (không phải file setup).
2. WHEN file `.exe` được tìm thấy, THE Launcher SHALL khởi chạy file đó ngay lập tức.
3. IF không tìm thấy file `.exe` nào trong thư mục phiên bản, THEN THE Launcher SHALL hiển thị thông báo lỗi "Không tìm thấy file thực thi".

---

### Requirement 5: Cài đặt và chạy ứng dụng Installable

**User Story:** Là người dùng, tôi muốn được hỏi trước khi cài đặt và thấy tiến trình cài đặt, để tôi biết chuyện gì đang xảy ra.

#### Acceptance Criteria

1. WHEN người dùng nhấn vào Version_Card của một Installable_App mà chưa được cài đặt, THE Launcher SHALL hiển thị hộp thoại xác nhận với nội dung "Phần mềm chưa được cài đặt, bạn có muốn cài không?" và hai nút "Cài đặt" và "Hủy".
2. WHEN người dùng nhấn "Cài đặt", THE Launcher SHALL thực hiện Silent_Install bằng cách chạy Setup_File với tham số `/S` (cho `.exe`) hoặc `/quiet /norestart` (cho `.msi`).
3. WHILE quá trình Silent_Install đang chạy, THE Launcher SHALL hiển thị trạng thái "Đang cài đặt...".
4. WHEN Silent_Install hoàn tất thành công, THE Launcher SHALL hiển thị thông báo "Cài đặt hoàn tất" và tự động khởi chạy ứng dụng vừa cài.
5. IF Silent_Install thất bại (exit code khác 0), THEN THE Launcher SHALL hiển thị thông báo lỗi "Cài đặt thất bại. Vui lòng thử lại."
6. WHEN người dùng nhấn "Hủy", THE Launcher SHALL đóng hộp thoại và không thực hiện bất kỳ hành động nào.

---

### Requirement 6: Tự nhận dạng đường dẫn cài đặt

**User Story:** Là người dùng, tôi muốn ứng dụng tự tìm đường dẫn cài đặt sau khi cài xong, để tôi không cần tìm thủ công.

#### Acceptance Criteria

1. WHEN Silent_Install hoàn tất, THE Install_Path_Resolver SHALL tra cứu registry Windows tại `HKLM\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall` và `HKCU\SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall` để tìm đường dẫn `InstallLocation` hoặc `DisplayIcon` của ứng dụng vừa cài.
2. IF Install_Path_Resolver tìm thấy đường dẫn hợp lệ chứa file `.exe`, THEN THE Launcher SHALL sử dụng đường dẫn đó để khởi chạy ứng dụng.
3. IF Install_Path_Resolver không tìm thấy đường dẫn qua registry, THEN THE Launcher SHALL tìm kiếm file `.exe` có tên trùng với tên ứng dụng trong `Program Files` và `Program Files (x86)`.
4. IF không tìm thấy đường dẫn sau tất cả các bước, THEN THE Launcher SHALL hiển thị thông báo "Không tìm thấy ứng dụng sau cài đặt. Vui lòng khởi chạy thủ công."

---

### Requirement 7: Giao diện dark theme phong cách xe đua

**User Story:** Là người dùng, tôi muốn giao diện tối, gradient đẹp mắt và chuyên nghiệp, để trải nghiệm phù hợp với phong cách xe đua.

#### Acceptance Criteria

1. THE Launcher SHALL áp dụng dark theme với màu nền chính từ Theme_Config.
2. THE Launcher SHALL hiển thị gradient trên các App_Card và Version_Card theo màu sắc định nghĩa trong Theme_Config.
3. THE Launcher SHALL hiển thị logo từ file `images/logo.png` ở vị trí header của giao diện.
4. THE Launcher SHALL sử dụng icon từ file `images/icon.ico` làm icon của cửa sổ ứng dụng.
5. WHERE Theme_Config tồn tại, THE Launcher SHALL tải toàn bộ cấu hình màu sắc, font chữ và kích thước từ file đó thay vì dùng giá trị mặc định.

---

### Requirement 8: Tách file cấu hình giao diện

**User Story:** Là nhà phát triển, tôi muốn cấu hình giao diện được tách thành file riêng, để tôi có thể tùy chỉnh logo, màu sắc và font chữ mà không cần sửa code chính.

#### Acceptance Criteria

1. THE Launcher SHALL đọc cấu hình giao diện từ một file Theme_Config riêng biệt (ví dụ: `theme.json` hoặc `theme.css`).
2. THE Theme_Config SHALL cho phép định nghĩa ít nhất: màu nền chính, màu gradient của card, màu chữ, font chữ, đường dẫn logo.
3. IF Theme_Config không tồn tại hoặc không hợp lệ, THEN THE Launcher SHALL sử dụng bộ giá trị mặc định và tiếp tục hoạt động bình thường.
