import streamlit as st
import requests
import json
import pandas as pd
from datetime import datetime
import time

# Cấu hình page
st.set_page_config(
    page_title="Hệ thống QLDT - Danh sách môn học",
    page_icon="📚",
    layout="wide"
)

# CSS tùy chỉnh
st.markdown("""
<style>
    .main-header {
        text-align: center;
        color: #2E86AB;
        margin-bottom: 30px;
    }
    .success-message {
        background-color: #D4EDDA;
        border: 1px solid #C3E6CB;
        color: #155724;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .error-message {
        background-color: #F8D7DA;
        border: 1px solid #F5C6CB;
        color: #721C24;
        padding: 10px;
        border-radius: 5px;
        margin: 10px 0;
    }
    .course-card {
        background-color: #F8F9FA;
        border: 1px solid #DEE2E6;
        border-radius: 8px;
        padding: 15px;
        margin: 10px 0;
    }
</style>
""", unsafe_allow_html=True)

# API functions - Sử dụng API thực tế của FTUGate
class QLDTApi:
    def __init__(self):
        self.base_url = "https://ftugate.ftu.edu.vn"
        self.default_headers = {
            'Content-Type': 'application/json',
            'Accept': 'application/json, text/plain, */*',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Safari/537.36',
            'Origin': 'https://ftugate.ftu.edu.vn',
            'Referer': 'https://ftugate.ftu.edu.vn/',
            'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8',
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'sec-ch-ua': '"Google Chrome";v="137", "Chromium";v="137", "Not/A)Brand";v="24"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin'
        }
    
    def _post(self, path, data=None, json=None, token=None, content_type=None):
        url = f"{self.base_url}{path}"
        proxies = {
            'http': 'http://113.160.132.195:8080',
            'https': 'http://113.160.132.195:8080'
        }
        headers = self.default_headers.copy()
        if token: headers['Authorization'] = f'Bearer {token}'
        if content_type: headers['Content-Type'] = content_type
        resp = requests.post(url, data=data, json=json, proxies=proxies, headers=headers)
        resp.raise_for_status()
        return resp.json()
    
    def login(self, username, password):
        """Đăng nhập vào hệ thống QLDT"""
        return self._post(
            '/api/auth/login',
            data={'username':username, 'password':password, 'grant_type':'password'},
            content_type='application/x-www-form-urlencoded'
        )
    
    def get_registered_courses(self, token):
        """Lấy danh sách môn học đã đăng ký"""
        data = self._post(
            '/cq/hanoi/api/dkmh/w-locdskqdkmhsinhvien',
            json={'is_CVHT': False, 'is_Clear': True},
            token=token
        )
        
        courses = []
        
        # Kiểm tra nếu data là string
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return {
                    'courses': [],
                    'total_credits': 0,
                    'total_courses': 0,
                    'raw_data': {'raw_response': data},
                    'error': 'Dữ liệu trả về không đúng định dạng JSON'
                }
        
        # Xử lý dữ liệu sau khi đảm bảo đã parse thành object
        if isinstance(data, dict) and 'data' in data:
            data_section = data['data']
            
            # Kiểm tra nếu có ds_kqdkmh trong data
            if 'ds_kqdkmh' in data_section and isinstance(data_section['ds_kqdkmh'], list):
                for course_record in data_section['ds_kqdkmh']:
                    if isinstance(course_record, dict) and 'to_hoc' in course_record:
                        to_hoc = course_record['to_hoc']
                        
                        # Xử lý thời khóa biểu
                        tkb = to_hoc.get('tkb', '')
                        # Tách thông tin giảng viên từ tkb
                        lecturer = ''
                        if 'GV ' in tkb:
                            parts = tkb.split('GV ')
                            if len(parts) > 1:
                                lecturer_part = parts[1].split(',')[0]
                                lecturer = lecturer_part.strip()
                        
                        # Tách thông tin thời gian học
                        schedule = ''
                        if tkb:
                            # Lấy phần đầu tiên của tkb để hiển thị thời gian chính
                            schedule_parts = tkb.split('<hr>')
                            if schedule_parts:
                                first_schedule = schedule_parts[0]
                                # Tách thông tin thứ và tiết
                                if 'tiết' in first_schedule:
                                    schedule = first_schedule.split(',GV')[0] if ',GV' in first_schedule else first_schedule
                        
                        course_info = {
                            'course_id': to_hoc.get('ma_mon', ''),
                            'course_name': to_hoc.get('ten_mon', ''),
                            'credits': int(to_hoc.get('so_tc', 0)) if to_hoc.get('so_tc', '').isdigit() else 0,
                            'lecturer': lecturer,
                            'schedule': schedule,
                            'room': '',  # Không có thông tin phòng học rõ ràng trong dữ liệu
                            'semester': '',  # Có thể lấy từ ngày học
                            'status': course_record.get('trang_thai_mon', ''),
                            'group_id': to_hoc.get('id_to_hoc', ''),
                            'class_name': to_hoc.get('lop', ''),
                            'week_schedule': tkb,  # Lưu toàn bộ thời khóa biểu
                            'group_number': to_hoc.get('nhom_to', ''),
                            'registration_date': course_record.get('ngay_dang_ky', ''),
                            'english_name': to_hoc.get('ten_mon_eg', '').strip()
                        }
                        courses.append(course_info)
        
        return {
            'courses': courses,
            'total_credits': sum(course['credits'] for course in courses if isinstance(course['credits'], (int, float))),
            'total_courses': len(courses),
            'total_items': data_section.get('total_items', len(courses)),
            'min_credits': data_section.get('so_tin_chi_min', 0),
            'raw_data': data
        }
    
    def get_sections(self, token):
        """Lấy danh sách nhóm tổ học và danh sách môn trong học kỳ"""
        data = self._post(
            '/cq/hanoi/api/dkmh/w-locdsnhomto',
            json={
                'is_CVHT': False,
                'additional': {
                    'paging': {'limit': 99999, 'page': 1},
                    'ordering': [{'name': '', 'order_type': ''}]
                }
            },
            token=token
        )
        return {
            'ds_nhom_to': data.get('data', {}).get('ds_nhom_to', []),
            'ds_mon_hoc': data.get('data', {}).get('ds_mon_hoc', [])
        }
    
    def register_course(self, token, id_to_hoc):
        """Đăng ký một môn học"""
        return self._post(
            '/cq/hanoi/api/dkmh/w-xulydkmhsinhvien',
            json={'filter': {'id_to_hoc': id_to_hoc, 'is_checked': True, 'sv_nganh': 1}},
            token=token
        )
    
    def logout(self, token):
        """Đăng xuất khỏi hệ thống"""
        try:
            return self._post('/api/auth/logout', json={}, token=token)
        except:
            return {'success': True, 'message': 'Logged out (token may have expired)'}

# Khởi tạo API
api = QLDTApi()

# Khởi tạo session state gọn hơn
for k,v in {'logged_in': False, 'user_info': None, 'token': None, 'courses_data': None}.items():
    st.session_state.setdefault(k, v)

# Header chính
st.markdown('<h1 class="main-header">🎓 Hệ thống Quản lý Đào tạo - Danh sách môn học</h1>', 
            unsafe_allow_html=True)

# Sidebar cho đăng nhập
with st.sidebar:
    st.header("🔐 Đăng nhập")
    
    # Hiển thị trạng thái kết nối
    st.write("**Trạng thái:** 🟢 Kết nối API thực")
    st.write("**Server:** ftugate.ftu.edu.vn")
    
    if not st.session_state.logged_in:
        with st.form("login_form"):
            username = st.text_input("Tên đăng nhập:")
            password = st.text_input("Mật khẩu:", type="password")
            login_button = st.form_submit_button("Đăng nhập")
        
        if login_button:
            if username and password:
                try:
                    with st.spinner("Đang đăng nhập..."):
                        login_data = api.login(username, password)
                        st.session_state.logged_in = True
                        st.session_state.user_info = login_data
                        st.session_state.token = login_data["access_token"]
                        st.session_state.login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        st.success("Đăng nhập thành công!")
                        time.sleep(1)
                        st.rerun()
                except Exception as e:
                    st.error(f"Lỗi đăng nhập: {str(e)}")
            else:
                st.error("Vui lòng nhập đầy đủ thông tin!")
    else:
        user_info = st.session_state.user_info
        st.success(f"Xin chào {user_info.get('name', user_info.get('username', 'N/A'))}!")
        
        # Hiển thị thông tin user từ API
        if 'username' in user_info:
            st.write(f"**Tên đăng nhập:** {user_info['username']}")
        if 'name' in user_info:
            st.write(f"**Họ tên:** {user_info['name']}")
        if 'student_id' in user_info:
            st.write(f"**Mã SV:** {user_info['student_id']}")
        if 'expires_in' in user_info:
            st.write(f"**Token hết hạn:** {user_info['expires_in']}s")
        
        # Hiển thị thời gian đăng nhập
        if 'login_time' in st.session_state:
            st.write(f"**Đăng nhập lúc:** {st.session_state.login_time}")
        
        if st.button("Đăng xuất"):
            try:
                with st.spinner("Đang đăng xuất..."):
                    api.logout(st.session_state.token)
                    st.session_state.logged_in = False
                    st.session_state.user_info = None
                    st.session_state.token = None
                    st.session_state.courses_data = None
                    if 'login_time' in st.session_state:
                        del st.session_state.login_time
                    st.success("Đã đăng xuất thành công!")
                    time.sleep(1)
                    st.rerun()
            except Exception as e:
                st.error(f"Lỗi đăng xuất: {str(e)}")
                # Vẫn xóa session state ngay cả khi đăng xuất lỗi
                st.session_state.logged_in = False
                st.session_state.user_info = None
                st.session_state.token = None
                st.session_state.courses_data = None
                if 'login_time' in st.session_state:
                    del st.session_state.login_time

# Main content
if st.session_state.logged_in:
    st.markdown("---")
    
    # Nút tải danh sách môn học
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        if st.button("📋 Tải danh sách môn học đã đăng ký", use_container_width=True):
            try:
                with st.spinner("Đang tải danh sách môn học..."):
                    courses_data = api.get_registered_courses(st.session_state.token)
                    st.session_state.courses_data = courses_data
                    st.rerun()
            except Exception as e:
                st.error(f"Lỗi tải danh sách: {str(e)}")
    
    # Hiển thị danh sách môn học
    if st.session_state.courses_data:
        st.markdown("---")
        st.header("📚 Danh sách môn học đã đăng ký")
        
        # Kiểm tra nếu có lỗi
        if 'error' in st.session_state.courses_data:
            st.error(f"Lỗi: {st.session_state.courses_data['error']}")
            st.write("**Dữ liệu Raw để debug:**")
            st.json(st.session_state.courses_data.get('raw_data', {}))
            st.stop()
        
        # Thống kê tổng quan
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Tổng số môn học", st.session_state.courses_data["total_courses"])
        with col2:
            st.metric("Tổng số tín chỉ", st.session_state.courses_data["total_credits"])
        with col3:
            if 'total_items' in st.session_state.courses_data:
                st.metric("Tổng items", st.session_state.courses_data["total_items"])
            else:
                st.metric("Học kỳ", "2024.1")
        with col4:
            if 'min_credits' in st.session_state.courses_data:
                st.metric("Tín chỉ tối thiểu", st.session_state.courses_data["min_credits"])
            else:
                st.metric("Trạng thái", "Đang học")
        
        st.markdown("---")
        
        # Hiển thị từng môn học
        courses = st.session_state.courses_data["courses"]
        
        if courses:
            for i, course in enumerate(courses, 1):
                with st.expander(f"📖 {course['course_id']} - {course['course_name']}", expanded=True):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write(f"**Mã môn học:** {course['course_id']}")
                        st.write(f"**Tên môn học:** {course['course_name']}")
                        if course.get('english_name'):
                            st.write(f"**Tên tiếng Anh:** {course['english_name']}")
                        st.write(f"**Số tín chỉ:** {course['credits']}")
                        st.write(f"**Trạng thái:** {course['status']}")
                        if course.get('group_number'):
                            st.write(f"**Nhóm:** {course['group_number']}")
                        if course.get('registration_date'):
                            st.write(f"**Ngày đăng ký:** {course['registration_date']}")
                    
                    with col2:
                        st.write(f"**Giảng viên:** {course['lecturer']}")
                        st.write(f"**Thời gian:** {course['schedule']}")
                        if course.get('room'):
                            st.write(f"**Phòng học:** {course['room']}")
                        if course.get('class_name'):
                            st.write(f"**Lớp:** {course['class_name']}")
                        if course.get('group_id'):
                            st.write(f"**Mã nhóm:** {course['group_id']}")
                    
                    # Hiển thị thời khóa biểu chi tiết
                    if course.get('week_schedule'):
                        st.write("**Thời khóa biểu chi tiết:**")
                        schedule_parts = course['week_schedule'].split('<hr>')
                        for part in schedule_parts:
                            if part.strip():
                                st.write(f"• {part.strip()}")
        else:
            st.info("Không có môn học nào được đăng ký trong học kỳ này.")
        
        # Xuất dữ liệu
        st.markdown("---")
        st.subheader("📊 Xuất dữ liệu")
        
        # Tạo tabs cho các chức năng khác nhau
        tab1, tab2, tab3 = st.tabs(["📋 Bảng dữ liệu", "📥 Tải xuống", "🔍 Dữ liệu Raw"])
        
        with tab1:
            # Hiển thị bảng
            if courses:
                df = pd.DataFrame(courses)
                st.dataframe(df, use_container_width=True)
            else:
                st.info("Không có dữ liệu để hiển thị")
        
        with tab2:
            if courses:
                df = pd.DataFrame(courses)
                
                col1, col2 = st.columns(2)
                
                with col1:
                    # Nút download CSV
                    csv = df.to_csv(index=False, encoding='utf-8-sig')
                    st.download_button(
                        label="📥 Tải xuống CSV",
                        data=csv,
                        file_name=f"danh_sach_mon_hoc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                        mime="text/csv",
                        use_container_width=True
                    )
                
                with col2:
                    # Xuất JSON
                    json_data = json.dumps(st.session_state.courses_data, 
                                         ensure_ascii=False, indent=2)
                    st.download_button(
                        label="📥 Tải xuống JSON",
                        data=json_data,
                        file_name=f"danh_sach_mon_hoc_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                        mime="application/json",
                        use_container_width=True
                    )
            else:
                st.info("Không có dữ liệu để tải xuống")
        
        with tab3:
            st.write("**Dữ liệu Raw từ API:**")
            if 'raw_data' in st.session_state.courses_data:
                st.json(st.session_state.courses_data['raw_data'])
            else:
                st.json(st.session_state.courses_data)

else:
    # Hiển thị thông báo khi chưa đăng nhập
    st.info("👈 Vui lòng đăng nhập để xem danh sách môn học đã đăng ký")
    
    # Hiển thị hướng dẫn
    st.markdown("---")
    st.subheader("📝 Hướng dẫn sử dụng")
    st.write("1. **Đăng nhập:** Nhập tên đăng nhập và mật khẩu FTUGate vào sidebar")
    st.write("2. **Xác thực:** Nhấn nút 'Đăng nhập' để kết nối tới server thực")
    st.write("3. **Tải dữ liệu:** Sau khi đăng nhập thành công, nhấn 'Tải danh sách môn học đã đăng ký'")
    st.write("4. **Xem thông tin:** Xem thông tin chi tiết từng môn học đã đăng ký")
    st.write("5. **Xuất dữ liệu:** Sử dụng các tab để xem bảng, tải xuống CSV/JSON, hoặc xem dữ liệu Raw")
    
    st.markdown("---")
    st.subheader("⚠️ Lưu ý quan trọng")
    st.warning("🔒 Ứng dụng này kết nối trực tiếp với server FTUGate. Vui lòng sử dụng tài khoản thực của bạn.")
    st.info("🔄 Nếu gặp lỗi đăng nhập, vui lòng kiểm tra lại thông tin tài khoản hoặc thử lại sau.")
    st.info("⏱️ Token đăng nhập có thể hết hạn, vui lòng đăng nhập lại nếu cần thiết.")

# Footer
st.markdown("---")
st.markdown(
    """
    <div style='text-align: center; color: #666; padding: 20px;'>
        <p>🎓 Hệ thống Quản lý Đào tạo - Phiên bản 1.0</p>
        <p>Được phát triển bằng Streamlit</p>
    </div>
    """, 
    unsafe_allow_html=True
)