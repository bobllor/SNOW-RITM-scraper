from dataclasses import dataclass

@dataclass
class Links:
    # the actual login page isn't used, the dashboard will always be the first page seen logging in.
    dashboard: str = 'https://tek.service-now.com/navpage.do'
    vtb: str = 'https://tek.service-now.com/nav_to.do?uri=%2F$vtb.do%3Fsysparm_board%3D43c1517e8780b0d0a6df2f47cebb3523'
    new_user: str = 'https://tek.service-now.com/nav_to.do?uri=%2Fsys_user.do%3Fsys_id%3D-1%26sys_is_list%3Dtrue%26sys_target%3Dsys_user%26sysparm_checked_items%3D%26sysparm_fixed_query%3D%26sysparm_group_sort%3D%26sysparm_list_css%3D%26sysparm_query%3DGOTO123TEXTQUERY321%3DDavid%2BKvachev%26sysparm_referring_url%3Dsys_user_list.do%3Fsysparm_query%3DGOTO123TEXTQUERY321%253DDavid%2BKvachev@99@sysparm_first_row%3D1%26sysparm_target%3D%26sysparm_view%3D'
    