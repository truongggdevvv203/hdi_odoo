# HDI Payroll Module - Hệ thống Tính Lương

## Tổng quan

**HDI Payroll** là một module tính lương custom toàn diện cho **Odoo 18 Community Edition**, được thiết kế riêng cho doanh nghiệp HDI với các quy trình tính lương theo đặc thù Việt Nam.

### Đặc điểm chính

✅ **Tính lương tự động** từ bảng công  
✅ **Hệ số lương** theo chức danh và level  
✅ **Công thức tính lương linh hoạt** (Python-based)  
✅ **Tích hợp với HR Attendance & Holidays**  
✅ **Xuất phiếu lương** chi tiết  
✅ **Hỗ trợ đầy đủ** các khoản thuế và bảo hiểm  
✅ **Ghi chú và theo dõi** toàn bộ quá trình  

---

## 📋 KIẾN TRÚC HỆ THỐNG

### Workflow Tính Lương Đầy Đủ

```
Attendance (HR Attendance)
    ↓
Work Summary (Bảng công)
    ↓
Salary Grade (Hệ số lương)
    ↓
Salary Structure (Cấu trúc lương)
    ↓
Salary Rules (Công thức tính)
    ↓
Payslip (Phiếu lương)
```

---

## 🔧 CÁC MODEL CHÍNH

### 1. **hr.work.summary** - Bảng Công

Tóm tắt dữ liệu công việc của nhân viên từ attendance & leaves.

**Các trường:**

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `employee_id` | Many2one | Nhân viên |
| `date` | Date | Ngày |
| `work_hours` | Float | Số giờ làm việc |
| `work_day` | Float | Ngày công (0, 0.5, 1) |
| `late_minutes` | Integer | Phút đi muộn |
| `early_minutes` | Integer | Phút về sớm |
| `paid_leave` | Float | Ngày nghỉ có lương |
| `unpaid_leave` | Float | Ngày nghỉ không lương |
| `notes` | Text | Ghi chú |

**Cách sử dụng:**

```python
# Tự động tính từ attendance
summary.action_generate_from_attendance()

# Tự động tính từ holidays
summary.action_generate_from_leaves()
```

---

### 2. **hr.salary.grade** - Hệ Số Lương

Định nghĩa lương cơ bản theo chức danh và level.

**Các trường:**

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `job_id` | Many2one | Chức danh (HR Job) |
| `level` | Selection | Level (intern, junior, middle, senior, lead, manager) |
| `base_salary` | Monetary | Lương cơ bản |
| `coefficient` | Float | Hệ số lương (1.0 = 100%) |
| `allowance` | Monetary | Phụ cấp cố định |
| `company_id` | Many2one | Công ty |

**Ví dụ:**

- Developer - Junior: Base = 7M VND, Hệ số = 1.0, Phụ cấp = 500K VND
- Developer - Middle: Base = 10M VND, Hệ số = 1.2, Phụ cấp = 1M VND
- Developer - Senior: Base = 15M VND, Hệ số = 1.5, Phụ cấp = 1.5M VND

**Công thức tính lương hàng ngày:**

```
Lương/ngày = (Base × Hệ số) / 26
Lương tháng = Lương/ngày × Số ngày công
```

---

### 3. **hr.salary.structure** - Cấu Trúc Lương

Định nghĩa cấu trúc lương: các thành phần nào sẽ được tính.

**Các trường:**

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `name` | Char | Tên cấu trúc |
| `rule_ids` | One2many | Danh sách salary rules |
| `company_id` | Many2one | Công ty |
| `active` | Boolean | Hoạt động |

**Ví dụ:** "Cấu trúc lương tiêu chuẩn HDI"
- Bao gồm: Basic Salary, Allowance, Paid Leave, Unpaid Leave Deduction, Insurance (BHXH/BHYT/BHTN)

---

### 4. **hr.salary.rule** - Công Thức Tính Lương

Mỗi rule là một phần tử trong cấu trúc lương.

**Các trường:**

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `name` | Char | Tên rule |
| `code` | Char | Mã code (BASIC, ALLOWANCE, PAID_LEAVE, ...) |
| `structure_id` | Many2one | Cấu trúc lương |
| `category` | Selection | basic / allowance / deduction / insurance / tax |
| `sequence` | Integer | Thứ tự tính (1, 2, 3, ...) |
| `python_condition` | Text | Điều kiện Python (True/False) |
| `python_compute` | Text | Công thức tính Python |

**Biến có sẵn trong Python Code:**

```python
employee          # Đối tượng hr.employee
payslip          # Đối tượng phiếu lương hiện tại
worked_days      # Số ngày công
paid_leave       # Ngày nghỉ có lương
unpaid_leave     # Ngày nghỉ không lương
base_salary      # Lương cơ bản
coefficient      # Hệ số lương
env              # Odoo environment
```

**Ví dụ Rules:**

```python
# Rule 1: Lương cơ bản
code: BASIC
python_compute: result = (base_salary * coefficient / 26) * worked_days

# Rule 2: Phụ cấp
code: ALLOWANCE
python_compute: result = 500000  # hoặc từ salary grade

# Rule 3: Ngày nghỉ có lương
code: PAID_LEAVE
python_condition: paid_leave > 0
python_compute: result = (base_salary * coefficient / 26) * paid_leave

# Rule 4: Trừ ngày nghỉ không lương
code: UNPAID_LEAVE
python_condition: unpaid_leave > 0
python_compute: result = (base_salary * coefficient / 26) * unpaid_leave

# Rule 5: BHXH (8%)
code: SOCIAL_INSURANCE
python_compute: result = (BASIC + ALLOWANCE) * 0.08

# Rule 6: BHYT (1.5%)
code: HEALTH_INSURANCE
python_compute: result = (BASIC + ALLOWANCE) * 0.015

# Rule 7: BHTN (0.5%)
code: UNEMPLOYMENT_INSURANCE
python_compute: result = (BASIC + ALLOWANCE) * 0.005
```

---

### 5. **hr.payslip** - Phiếu Lương

Phiếu lương của nhân viên cho một kỳ (tháng).

**Các trường:**

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `name` | Char | Số phiếu lương (tự động) |
| `employee_id` | Many2one | Nhân viên |
| `date_from` | Date | Ngày bắt đầu kỳ |
| `date_to` | Date | Ngày kết thúc kỳ |
| `salary_structure_id` | Many2one | Cấu trúc lương áp dụng |
| `worked_days` | Float | Ngày công (tính tự động) |
| `paid_leave` | Float | Ngày nghỉ có lương (tính tự động) |
| `unpaid_leave` | Float | Ngày nghỉ không lương (tính tự động) |
| `base_salary` | Monetary | Lương cơ bản (từ salary grade) |
| `coefficient` | Float | Hệ số lương |
| `line_ids` | One2many | Chi tiết các dòng lương |
| `gross_salary` | Monetary | Lương gross (tính tự động) |
| `deduction_total` | Monetary | Tổng khoản trừ (tính tự động) |
| `net_salary` | Monetary | Lương net (tính tự động) |
| `state` | Selection | draft / compute / done / cancel |

**Trạng thái Payslip:**

1. **Draft (Nháp)**: Phiếu mới tạo
2. **Compute (Tính toán)**: Đã tính toán chi tiết
3. **Done (Hoàn thành)**: Đã xác nhận
4. **Cancel (Hủy)**: Hủy phiếu

---

### 6. **hr.payslip.line** - Dòng Chi Tiết Phiếu Lương

Mỗi dòng là kết quả tính của một salary rule.

**Các trường:**

| Trường | Kiểu | Mô tả |
|--------|------|-------|
| `payslip_id` | Many2one | Phiếu lương |
| `rule_id` | Many2one | Rule tính lương |
| `name` | Char | Tên dòng |
| `code` | Char | Mã code |
| `category` | Selection | Loại (basic, allowance, deduction, ...) |
| `amount` | Monetary | Số tiền |

---

## 🚀 HƯỚNG DẪN SỬ DỤNG

### Bước 1: Cài đặt Module

```bash
# Cách 1: CLI
./odoo-bin --addons-path=. -d [database] -u hdi_payroll

# Cách 2: Web UI
1. Vào Settings → Modules
2. Tìm "HDI Payroll"
3. Bấm "Install"
```

### Bước 2: Tạo Salary Grade

1. Vào **Tính Lương > Cấu hình lương > Hệ số lương**
2. Bấm **Create**
3. Điền thông tin:
   - **Chức danh**: Chọn job (ví dụ: Developer)
   - **Level**: Chọn level (ví dụ: Middle)
   - **Lương cơ bản**: 10,000,000 VND
   - **Hệ số lương**: 1.2
   - **Phụ cấp**: 1,000,000 VND
4. Bấm **Save**

### Bước 3: Tạo Salary Structure & Rules

**Mặc định đã có** "Cấu trúc lương tiêu chuẩn HDI" với các rules:

- Lương cơ bản (BASIC)
- Phụ cấp (ALLOWANCE)
- Ngày nghỉ có lương (PAID_LEAVE)
- Trừ ngày nghỉ không lương (UNPAID_LEAVE)
- BHXH, BHYT, BHTN
- Thuế TNCN

Có thể **tạo thêm structure** khác nếu cần.

### Bước 4: Nhập Bảng Công (Work Summary)

**Cách 1: Manual**

1. Vào **Tính Lương > Bảng công**
2. Bấm **Create**
3. Điền:
   - **Nhân viên**: Chọn
   - **Ngày**: Ngày công việc
   - **Ngày công**: 1 (cả ngày) hoặc 0.5 (nửa ngày)
   - **Ngày nghỉ có lương**: Điền nếu có
   - **Ngày nghỉ không lương**: Điền nếu có
4. Bấm **Save**

**Cách 2: Auto từ Attendance (Tương lai)**

```python
summary = work_summary.browse(id)
summary.action_generate_from_attendance()  # Tính từ check-in/out
summary.action_generate_from_leaves()      # Tính từ holidays
```

### Bước 5: Tạo Phiếu Lương (Payslip)

1. Vào **Tính Lương > Phiếu lương**
2. Bấm **Create**
3. Điền:
   - **Nhân viên**: Chọn
   - **Từ ngày**: 01/12/2024
   - **Đến ngày**: 31/12/2024
   - **Cấu trúc lương**: Chọn (mặc định = Cấu trúc tiêu chuẩn)
4. Các trường dưới sẽ tự động điền:
   - **Ngày công** (từ Work Summary)
   - **Lương cơ bản** (từ Salary Grade)
5. Bấm **Tính lương** → Hệ thống tính tất cả các dòng
6. Bấm **Xác nhận** → Hoàn thành phiếu

---

## 📊 VÍ DỤ TÍNH LƯƠNG THỰC TẾ

### Input:

| Thông tin | Giá trị |
|-----------|--------|
| Nhân viên | Nguyễn Văn A |
| Chức danh | Developer |
| Level | Middle |
| Lương cơ bản | 10,000,000 VND |
| Hệ số | 1.2 |
| Phụ cấp | 1,000,000 VND |
| Ngày công | 22 ngày |
| Ngày nghỉ có lương | 1 ngày |
| Ngày nghỉ không lương | 0 ngày |

### Tính toán:

```
Lương/ngày = (10M × 1.2) / 26 = 461,538 VND

1. Lương cơ bản = 461,538 × 22 = 10,153,846 VND
2. Phụ cấp = 1,000,000 VND
3. Ngày nghỉ có lương = 461,538 × 1 = 461,538 VND
4. Trừ ngày nghỉ không lương = 0 VND

Subtotal (Gross) = 10,153,846 + 1,000,000 + 461,538 = 11,615,384 VND

5. BHXH (8%) = 11,615,384 × 0.08 = 929,231 VND
6. BHYT (1.5%) = 11,615,384 × 0.015 = 174,231 VND
7. BHTN (0.5%) = 11,615,384 × 0.005 = 58,077 VND
8. Thuế TNCN = 0 VND (placeholder)

Tổng khoản trừ = 929,231 + 174,231 + 58,077 = 1,161,538 VND

Lương NET = 11,615,384 - 1,161,538 = 10,453,846 VND
```

### Output Payslip:

| Dòng | Loại | Số tiền |
|-----|------|--------|
| Lương cơ bản | Basic | 10,153,846 |
| Phụ cấp | Allowance | 1,000,000 |
| Ngày nghỉ có lương | Allowance | 461,538 |
| BHXH | Insurance | -929,231 |
| BHYT | Insurance | -174,231 |
| BHTN | Insurance | -58,077 |
| **Lương Gross** | | **11,615,384** |
| **Tổng khoản trừ** | | **-1,161,538** |
| **Lương NET** | | **10,453,846** |

---

## 🔐 QUYỀN HẠN (Access Control)

Các nhóm người dùng:

| Nhóm | Mô tả | Quyền |
|------|-------|------|
| **HR User** | Nhân viên HR | Đọc + Tạo/Sửa bảng công & phiếu |
| **HR Manager** | Quản lý HR | Toàn quyền |
| **System Admin** | Quản trị viên | Toàn quyền |

---

## ⚙️ TỰ ĐỘNG HÓA (Automation)

### Tự động tính từ Attendance:

```python
@api.model
def auto_generate_work_summary(self):
    """Tự động tạo work summary từ attendance cuối ngày"""
    # Chạy daily schedule
    attendances = self.env['hr.attendance'].search([
        ('date', '=', fields.Date.today())
    ])
    
    for att in attendances:
        summary, created = self.get_or_create(
            employee_id=att.employee_id.id,
            date=att.date
        )
        summary.action_generate_from_attendance()
```

### Tự động tính từ Holidays:

```python
@api.model
def auto_generate_leave_data(self):
    """Tự động cập nhật leave data cho work summary"""
    holidays = self.env['hr.holiday'].search([
        ('state', '=', 'validate'),
        ('date_from', '<=', fields.Date.today()),
        ('date_to', '>=', fields.Date.today()),
    ])
    
    for holiday in holidays:
        summaries = self.env['hr.work.summary'].search([
            ('employee_id', '=', holiday.employee_id.id),
            ('date', '>=', holiday.date_from.date()),
            ('date', '<=', holiday.date_to.date()),
        ])
        for summary in summaries:
            summary.action_generate_from_leaves()
```

---

## 🐛 TROUBLESHOOTING

### Vấn đề: Payslip không tính được

**Nguyên nhân:**
1. Work summary chưa được tạo
2. Salary grade chưa được tạo cho employee
3. Salary structure chưa được chọn

**Giải pháp:**
- Kiểm tra bảng công có dữ liệu không
- Kiểm tra employee có job_id không
- Kiểm tra salary grade có tồn tại cho job đó không

### Vấn đề: Python formula lỗi

**Nguyên nhân:** Syntax error trong python_compute

**Giải pháp:**
- Kiểm tra biến tên đúng chưa
- Kiểm tra phép tính có đúng không
- Test code Python trước khi đưa vào rule

---

## 📝 CUSTOMIZATION

### Thêm Rule Mới:

```python
# 1. Vào Tính Lương > Cấu hình lương > Rule tính lương
# 2. Bấm Create
# 3. Điền:
#    Name: "Phạt xin phép muộn"
#    Code: LATE_REQUEST_PENALTY
#    Structure: Cấu trúc tiêu chuẩn HDI
#    Category: Deduction
#    Sequence: 6
#    Python: result = 100000  # Phạt 100K
# 4. Save
```

### Tùy chỉnh Tax Calculation:

```python
# File: hr_salary_rule.py
# Tìm INCOME_TAX rule
# Cập nhật python_compute theo công thức thuế Việt Nam

# Ví dụ: Thuế bậc:
python_compute = """
taxable_income = BASIC + ALLOWANCE - (SOCIAL_INSURANCE + HEALTH_INSURANCE + UNEMPLOYMENT_INSURANCE)
if taxable_income < 5000000:
    result = 0
elif taxable_income < 10000000:
    result = (taxable_income - 5000000) * 0.05
else:
    result = 250000 + (taxable_income - 10000000) * 0.1
"""
```

---

## 📄 FILE STRUCTURE

```
hdi_payroll/
├── __init__.py
├── __manifest__.py
├── models/
│   ├── __init__.py
│   ├── hr_work_summary.py       # Bảng công
│   ├── hr_salary_grade.py       # Hệ số lương
│   ├── hr_salary_structure.py   # Cấu trúc lương
│   ├── hr_salary_rule.py        # Công thức
│   ├── hr_payslip.py            # Phiếu lương
│   └── hr_payslip_line.py       # Dòng chi tiết
├── views/
│   ├── hr_work_summary_views.xml
│   ├── hr_salary_grade_views.xml
│   ├── hr_salary_structure_views.xml
│   ├── hr_salary_rule_views.xml
│   ├── hr_payslip_views.xml
│   └── menu.xml
├── security/
│   └── ir.model.access.csv
├── data/
│   ├── hr_salary_grade_data.xml
│   ├── hr_salary_structure_data.xml
│   └── hr_salary_rule_data.xml
└── README.md
```

---

## 🔗 LIÊN KẾT & DEPENDENCIES

- **base** - Odoo Core
- **hr** - Human Resources
- **hr_attendance** - Attendance tracking
- **hr_holidays** - Leave management

---

## 📞 HỖ TRỢ & PHÁT TRIỂN

### Features Tương Lai:

- [ ] Tự động tính từ attendance (daily schedule)
- [ ] Export payslip to PDF
- [ ] Integration với kế toán (Accounting)
- [ ] Mẫu báo cáo lương
- [ ] Portal nhân viên xem lương
- [ ] Batch payslip tính cho nhiều nhân viên
- [ ] Import bảng công từ file Excel
- [ ] Dashboard thống kê lương

---

**Phiên bản:** 18.0.1.0.0  
**Cập nhật:** December 2024  
**Tác giả:** HDI  
**License:** LGPL-3
